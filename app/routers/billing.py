from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from yookassa import Configuration, Payment

from ..config import settings
from ..deps import get_db, get_current_user
from .. import crud, models

router = APIRouter(prefix="/billing", tags=["billing"])


def configure_yookassa():
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


@router.post("/buy-room")
def buy_room(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Создать платёж в ЮKassa для покупки ещё одной комнаты.
    Возвращаем ссылку на оплату (confirmation_url).
    """
    configure_yookassa()

    amount = settings.ROOM_PRICE_RUB
    description = f"Покупка дополнительной комнаты для пользователя {current_user.email}"

    # Генерируем idempotence_key (можно использовать user_id + что-то ещё)
    import uuid
    idempotence_key = str(uuid.uuid4())

    try:
        payment = Payment.create(
            {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB",
                },
                "confirmation": {
                    "type": "redirect",
                    # сюда ЮKassa отправит пользователя после оплаты
                    "return_url": "https://example.com/payment/success",
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": current_user.id,
                    "purpose": "buy_room",
                },
            },
            idempotence_key=idempotence_key,
        )
    except Exception as e:
        # В проде лучше логировать подробно
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e}")

    confirmation_url = payment.confirmation.confirmation_url
    payment_id = payment.id

    # Тут можно ничего не создавать в БД, только ждать webhook.
    # Или можно создать "pending" запись — но давай для простоты сделаем всё по webhook.

    return {
        "payment_id": payment_id,
        "amount": amount,
        "confirmation_url": confirmation_url,
    }


@router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook от ЮKassa. Здесь подтверждаем оплату и увеличиваем количество комнат.
    """
    configure_yookassa()

    body = await request.json()

    event = body.get("event")
    obj = body.get("object", {})

    # Нас интересует успешный платёж
    if event != "payment.succeeded":
        return {"status": "ignored"}

    payment_id = obj.get("id")
    amount_info = obj.get("amount", {})
    metadata = obj.get("metadata") or {}

    value_str = amount_info.get("value", "0.00")
    try:
        amount_rub = int(float(value_str))
    except ValueError:
        amount_rub = 0

    user_id = metadata.get("user_id")
    purpose = metadata.get("purpose")

    if purpose != "buy_room" or not user_id:
        return {"status": "ignored"}

    user = db.get(models.User, user_id)
    if not user:
        # Пользователь не найден — логируем, но не падаем
        return {"status": "user_not_found"}

    # Создаём запись подписки и увеличиваем max_rooms
    description = f"Оплата {amount_rub} ₽ за доп. комнату, платёж {payment_id}"
    crud.create_subscription_record_for_room(
        db=db,
        user=user,
        external_id=payment_id,
        amount_rub=amount_rub,
        description=description,
    )

    return {"status": "ok"}
