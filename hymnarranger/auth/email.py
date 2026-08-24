import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _get_api_instance():
    import sib_api_v3_sdk

    key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("SENDER_EMAIL")
    if not key or not sender:
        raise RuntimeError("BREVO_API_KEY або SENDER_EMAIL не задано. Перевір файл .env")
    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = key
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config)), sender


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException

    api, sender_email = _get_api_instance()
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": sender_email, "name": "HymnArranger"},
        subject="Відновлення паролю HymnArranger",
        html_content=f"""
            <p>Ви запросили відновлення паролю.</p>
            <p><a href="{reset_link}">Натисніть тут, щоб встановити новий пароль</a></p>
            <p>Посилання дійсне 30 хвилин. Якщо це були не ви — просто проігноруйте цей лист.</p>
        """,
    )
    try:
        api.send_transac_email(email)
    except ApiException as e:
        raise RuntimeError(f"Не вдалося надіслати лист: {e}")


def send_already_registered_email(to_email: str, login_link: str) -> None:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException

    api, sender_email = _get_api_instance()
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": sender_email, "name": "HymnArranger"},
        subject="Спроба реєстрації в HymnArranger",
        html_content=f"""
            <p>Хтось (можливо, ви) спробував зареєструватись із цією адресою.</p>
            <p>Обліковий запис із такою поштою вже існує.</p>
            <p><a href="{login_link}">Увійти до HymnArranger</a></p>
            <p>Якщо це були не ви — просто проігноруйте цей лист.</p>
        """,
    )
    try:
        api.send_transac_email(email)
    except ApiException as e:
        raise RuntimeError(f"Не вдалося надіслати лист: {e}")


def send_verification_email(to_email: str, verify_link: str) -> None:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException

    api, sender_email = _get_api_instance()
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": sender_email, "name": "HymnArranger"},
        subject="Підтвердження пошти HymnArranger",
        html_content=f"""
            <p>Дякуємо за реєстрацію в HymnArranger.</p>
            <p><a href="{verify_link}">Натисніть тут, щоб підтвердити пошту</a></p>
            <p>Посилання дійсне 24 години. Якщо це були не ви — просто проігноруйте цей лист.</p>
        """,
    )
    try:
        api.send_transac_email(email)
    except ApiException as e:
        raise RuntimeError(f"Не вдалося надіслати лист: {e}")


