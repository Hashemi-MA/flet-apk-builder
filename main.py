import flet as ft
import uuid
import json

from api import generate_otp, login
from storage import save_auth, load_auth, clear_auth, LOCAL_STORAGE_KEY

SITE_URL = "https://app.pakhshmart.com"
DEVICE_ID = str(uuid.uuid4())


def extract_auth_token(auth_data: dict) -> str:
    if not isinstance(auth_data, dict):
        return ""

    token_value = auth_data.get("token")

    if isinstance(token_value, dict):
        return token_value.get("authToken", "") or ""

    if isinstance(token_value, str):
        return token_value

    return ""


def normalize_auth_data(auth_data: dict) -> dict | None:
    if not isinstance(auth_data, dict):
        return None

    token_value = auth_data.get("token")

    # فرمت جدید
    if isinstance(token_value, dict) and token_value.get("authToken"):
        return auth_data

    # فرمت قدیمی
    if isinstance(token_value, str) and token_value:
        return {
            "token": {
                "authToken": token_value,
                "expiresIn": ""
            },
            "shopId": auth_data.get("shopId"),
            "mobile": auth_data.get("mobile", ""),
            "tagCode": auth_data.get("tagCode"),
            "activeDistributor": auth_data.get("activeDistributor"),
            "expirationDate": auth_data.get("expiration", ""),
            "errorMessage": None,
            "logingErrorCode": None,
        }

    return None


def main(page: ft.Page):
    page.title = "پخش مارت"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    raw_auth = load_auth()
    auth = normalize_auth_data(raw_auth)

    def make_local_storage_script(auth_data: dict) -> str:
        auth_json = json.dumps(auth_data, ensure_ascii=False)
        return f"""
(function() {{
    try {{
        localStorage.setItem("{LOCAL_STORAGE_KEY}", JSON.stringify({auth_json}));
        console.log("mart-user saved");
        setTimeout(function() {{
            window.location.reload();
        }}, 300);
    }} catch (e) {{
        console.error("localStorage injection failed:", e);
    }}
}})();
"""

    def show_webview(auth_data: dict):
        page.controls.clear()

        webview = ft.WebView(
            url=SITE_URL,
            expand=True,
            on_page_started=lambda e: print("loading..."),
            on_page_ended=lambda e: print("loaded"),
        )

        page.add(webview)
        page.update()

        async def inject():
            try:
                script = make_local_storage_script(auth_data)
                await webview.run_javascript(script)
            except Exception as ex:
                print("js inject error:", ex)

        page.run_task(inject)

    def show_otp_screen(mobile: str, remaining: int):
        otp_field = ft.TextField(
            label="کد OTP",
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=6,
            width=200,
        )
        status_text = ft.Text("", color=ft.Colors.RED)
        timer_text = ft.Text(f"انقضا: {remaining} ثانیه", size=12, color=ft.Colors.GREY)
        loading = ft.ProgressRing(visible=False, width=24, height=24)

        async def do_login(e):
            code = otp_field.value.strip()
            if len(code) < 4:
                status_text.value = "کد را وارد کنید"
                page.update()
                return

            loading.visible = True
            status_text.value = ""
            page.update()

            try:
                result = await login(mobile, code, DEVICE_ID)

                token_obj = result.get("token", {}) if isinstance(result, dict) else {}
                auth_token = token_obj.get("authToken", "") if isinstance(token_obj, dict) else ""
                error = result.get("errorMessage", "") if isinstance(result, dict) else "خطا در ورود"

                if auth_token:
                    save_auth(result)
                    show_webview(result)
                else:
                    status_text.value = error or "کد اشتباه است"
            except Exception as ex:
                status_text.value = f"خطا: {ex}"
            finally:
                loading.visible = False
                page.update()

        async def resend_otp(e):
            try:
                result = await generate_otp(mobile)
                error = result.get("errorMessage", "") if isinstance(result, dict) else ""

                if error:
                    status_text.value = error
                    status_text.color = ft.Colors.RED
                else:
                    status_text.value = "کد مجدداً ارسال شد"
                    status_text.color = ft.Colors.GREEN
            except Exception as ex:
                status_text.value = f"خطا: {ex}"
                status_text.color = ft.Colors.RED

            page.update()

        page.controls.clear()
        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.Text("کد OTP", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(f"کد ارسال شده به {mobile}", size=14),
                        timer_text,
                        otp_field,
                        ft.ElevatedButton("تأیید", on_click=do_login, width=200),
                        ft.TextButton("ارسال مجدد کد", on_click=resend_otp),
                        loading,
                        status_text,
                    ],
                ),
            )
        )
        page.update()

    def show_mobile_screen():
        mobile_field = ft.TextField(
            label="شماره موبایل",
            hint_text="09xxxxxxxxx",
            keyboard_type=ft.KeyboardType.PHONE,
            text_align=ft.TextAlign.CENTER,
            max_length=11,
            width=220,
        )
        status_text = ft.Text("", color=ft.Colors.RED)
        loading = ft.ProgressRing(visible=False, width=24, height=24)

        async def do_send_otp(e):
            mobile = mobile_field.value.strip()
            if len(mobile) != 11 or not mobile.startswith("09"):
                status_text.value = "شماره موبایل معتبر نیست"
                page.update()
                return

            loading.visible = True
            status_text.value = ""
            page.update()

            try:
                result = await generate_otp(mobile)
                remaining = result.get("remainingTime", 120) if isinstance(result, dict) else 120
                error = result.get("errorMessage", "") if isinstance(result, dict) else ""

                if error:
                    status_text.value = error
                    loading.visible = False
                    page.update()
                    return

                show_otp_screen(mobile, remaining)
            except Exception as ex:
                status_text.value = f"خطا در ارسال کد: {ex}"
                loading.visible = False
                page.update()

        page.controls.clear()
        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.Image(src="icon.png", width=80, height=80, error_content=ft.Text("🛒", size=60)),
                        ft.Text("پخش مارت", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("شماره موبایل خود را وارد کنید", size=14),
                        mobile_field,
                        ft.ElevatedButton("دریافت کد", on_click=do_send_otp, width=220),
                        loading,
                        status_text,
                    ],
                ),
            )
        )
        page.update()

    if auth and extract_auth_token(auth):
        show_webview(auth)
    else:
        show_mobile_screen()


#-- ft.app(target=main, view=ft.AppView.WEB_BROWSER)
ft.app(target=main)

