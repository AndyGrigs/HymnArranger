import os

import sib_api_v3_sdk
from dotenv import load_dotenv
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

if not BREVO_API_KEY or not SENDER_EMAIL:
    raise RuntimeError("BREVO_API_KEY або SENDER_EMAIL не задано. Перевір файл .env")

_config = sib_api_v3_sdk.Configuration()
_config.api_key["api-key"] = BREVO_API_KEY
_api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(_config))


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": SENDER_EMAIL, "name": "HymnArranger"},
        subject="Відновлення паролю HymnArranger",
        html_content=f"""
            <p>Ви запросили відновлення паролю.</p>
            <p><a href="{reset_link}">Натисніть тут, щоб встановити новий пароль</a></p>
            <p>Посилання дійсне 30 хвилин. Якщо це були не ви — просто проігноруйте цей лист.</p>
        """,
    )
    try:
        _api_instance.send_transac_email(email)
    except ApiException as e:
        raise RuntimeError(f"Не вдалося надіслати лист: {e}")