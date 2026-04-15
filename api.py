import logging
import os
import re
import uuid
from typing import Any, Optional

import httpx

# آدرس پایه API
BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://gw.pakhshmart.com/prdsaleonlinestore/api/Account",
)

# زمان انتظار پیش‌فرض هر درخواست
TIMEOUT = float(os.getenv("API_TIMEOUT", "15.0"))

logger = logging.getLogger("app.api")


class ApiError(Exception):
    """خطاهای مرتبط با API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (status={self.status_code})"
        return self.message


def get_device_id() -> str:
    """تولید شناسه یکتا برای دستگاه."""
    return str(uuid.uuid4())


def _normalize_mobile(mobile: str) -> str:
    """اعتبارسنجی شماره موبایل ایران با فرمت 09xxxxxxxxx."""
    value = (mobile or "").strip()
    if not re.fullmatch(r"09\d{9}", value):
        raise ApiError("فرمت شماره موبایل معتبر نیست.")
    return value


def _normalize_otp(code: str) -> str:
    """اعتبارسنجی کد OTP بین 4 تا 6 رقم."""
    value = (code or "").strip()
    if not re.fullmatch(r"\d{4,6}", value):
        raise ApiError("فرمت کد تأیید معتبر نیست.")
    return value


def _safe_json_parse(response: httpx.Response) -> Optional[dict]:
    """تلاش برای parse کردن پاسخ JSON به صورت امن."""
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        logger.warning("Failed to parse JSON response from %s", response.url)
        return None


def _extract_error_message(data: Any) -> str:
    """استخراج پیام خطا از ساختارهای مختلف پاسخ API."""
    if isinstance(data, dict):
        for key in (
            "errorMessage",
            "message",
            "error",
            "detail",
            "title",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        errors = data.get("errors")
        if isinstance(errors, dict):
            parts = []
            for key, value in errors.items():
                if isinstance(value, list) and value:
                    parts.append(f"{key}: {', '.join(map(str, value))}")
                elif value is not None and str(value).strip():
                    parts.append(f"{key}: {value}")
            if parts:
                return " | ".join(parts)

    return "عملیات با خطا مواجه شد."


async def _post(endpoint: str, payload: dict) -> dict:
    """ارسال درخواست POST و مدیریت خطاها."""
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    logger.debug("POST %s payload=%s", url, payload)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
    except httpx.TimeoutException as e:
        logger.warning("Timeout while calling %s", url)
        raise ApiError("مهلت درخواست به پایان رسید. لطفاً دوباره تلاش کنید.") from e
    except httpx.ConnectError as e:
        logger.warning("Connection error while calling %s", url)
        raise ApiError("اتصال به سرور برقرار نشد. اینترنت را بررسی کنید.") from e
    except httpx.RequestError as e:
        logger.warning("Request error while calling %s: %s", url, e)
        raise ApiError("خطا در ارتباط با سرور.") from e

    data = _safe_json_parse(response)

    if not response.is_success:
        message = _extract_error_message(data) if data else f"خطای HTTP {response.status_code}"
        logger.error("API error on %s: %s", url, message)
        raise ApiError(
            message=message,
            status_code=response.status_code,
            response_data=data,
        )

    if data is None:
        logger.error("Non-JSON response from %s", url)
        raise ApiError(
            "پاسخ نامعتبر از سرور دریافت شد.",
            status_code=response.status_code,
        )

    logger.debug("Response from %s: %s", url, data)
    return data


async def generate_otp(mobile: str) -> dict:
    """
    ارسال OTP به شماره موبایل.

    سازگار با main.py:
    - امضا: generate_otp(mobile)
    - خروجی: dict شامل remainingTime / remaining_time و در صورت نیاز errorMessage
    """
    mobile = _normalize_mobile(mobile)

    payload = {
        "mobileNumber": mobile,
        "otpStatus": 10,
    }

    try:
        data = await _post("GenerateOtp", payload)
    except ApiError as e:
        return {
            "success": False,
            "errorMessage": e.message,
            "remainingTime": 0,
            "remaining_time": 0,
            "raw_response": e.response_data,
            "status_code": e.status_code,
        }

    remaining_time = data.get("remainingTime")
    if remaining_time is None:
        remaining_time = data.get("remaining_time")
    if remaining_time is None:
        remaining_time = 120

    try:
        remaining_time = int(remaining_time)
    except (ValueError, TypeError):
        remaining_time = 120

    result = {
        "success": True,
        "errorMessage": "",
        "remainingTime": remaining_time,
        "remaining_time": remaining_time,
        "raw_response": data,
    }

    # اگر API خودش errorMessage برگرداند ولی HTTP 200 باشد
    if isinstance(data.get("errorMessage"), str) and data.get("errorMessage").strip():
        result["errorMessage"] = data["errorMessage"].strip()

    logger.info("OTP generated for %s, remaining_time=%s", mobile, remaining_time)
    return result

async def login(mobile: str, otp: str, device_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        payload = {
            "mobileNumber": mobile,
            "otpPassword": otp,
            "isAutoFilled": False,
            "deviceId": device_id,
        }
        print("LOGIN PAYLOAD:", payload)  # ← این خط را اضافه کن

        try:
            res = await client.post(
                f"{BASE_URL}/Login",
                json=payload,
                timeout=15,
            )
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as exc:
            print(f"API error on {exc.request.url}: {exc}")
            print("Response text:", exc.response.text)  # ← این خط را هم اضافه کن
            raise
