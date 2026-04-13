import httpx
import uuid

BASE_URL = "https://gw.pakhshmart.com/prdsaleonlinestore/api/Account"

def get_device_id() -> str:
    return str(uuid.uuid4())

async def generate_otp(mobile: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/GenerateOtp",
            json={"mobileNumber": mobile, "otpStatus": 10},
            timeout=15,
        )
        res.raise_for_status()
        return res.json()

async def login(mobile: str, otp: str, device_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/Login",
            json={
                "mobileNumber": mobile,
                "otpPassword": otp,
                "isAutoFilled": False,
                "deviceId": device_id,
            },
            timeout=15,
        )
        res.raise_for_status()
        return res.json()
