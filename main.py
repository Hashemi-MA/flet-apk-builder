import flet as ft
import asyncio
import uuid
from api import generate_otp, login
from storage import save_auth, load_auth, clear_auth

SITE_URL = "https://app.pakhshmart.com"
DEVICE_ID = str(uuid.uuid4())


def main(page: ft.Page):
    page.title = "پخش مارت"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    auth = load_auth()

    def show_webview():
        page.controls.clear()
        page.add(
            ft.WebView(
                url=SITE_URL,
                expand=True,
                on_page_started=lambda e: print("loading..."),
                on_page_ended=lambda e: print("loaded"),
            )
        )
        page.update()

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
                token_obj = result.get("token", {})
                auth_token = token_obj.get("authToken", "")
                expiration = token_obj.get("expirationDate", "")
                error = result.get("errorMessage", "")

                if auth_token:
                    save_auth(mobile, auth_token, expiration)
                    show_webview()
                else:
                    status_text.value = error or "کد اشتباه است"
            except Exception as ex:
                status_text.value = f"خطا: {ex}"
            finally:
                loading.visible = False
                page.update()

        async def resend_otp(e):
            try:
                await generate_otp(mobile)
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
                remaining = result.get("remainingTime", 120)
                error = result.get("errorMessage", "")

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

    if auth and auth.get("token"):
        show_webview()
    else:
        show_mobile_screen()


ft.app(target=main)
