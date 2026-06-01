"""
Notifications — Webhook Notifier.

POST booking summaries to a webhook endpoint.
"""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


class WebhookNotifier:

    TIMEOUT = 10

    MAX_RETRIES = 2

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        webhook_url=None,
    ):

        self.webhook_url = webhook_url

        if webhook_url:

            logger.info(
                f"WebhookNotifier initialized "
                f"(url={webhook_url[:40]}...)"
            )

        else:

            logger.warning(
                "Webhook URL missing. "
                "Webhook notifications disabled."
            )

    # =====================================================
    # SEND NOTIFICATION
    # =====================================================

    def send_notification(
        self,
        booking_data,
    ):

        # =================================================
        # DISABLED
        # =================================================

        if not self.webhook_url:

            logger.warning(
                "Webhook skipped because "
                "webhook_url is empty."
            )

            return False

        # =================================================
        # SUPPORT BOTH DICT + OBJECT
        # =================================================

        if isinstance(
            booking_data,
            dict,
        ):

            payload = {

                "booking_id":
                    booking_data.get(
                        "event_id",
                        "pending",
                    ),

                "service":
                    booking_data.get(
                        "service_type"
                    ),

                "date":
                    booking_data.get(
                        "date"
                    ),

                "time":
                    booking_data.get(
                        "time"
                    ),

                "customer_name":
                    booking_data.get(
                        "name"
                    ),

                "contact":
                    booking_data.get(
                        "contact"
                    ),

                "email":
                    booking_data.get(
                        "email"
                    ),

                "confirmed":
                    booking_data.get(
                        "confirmed",
                        True,
                    ),

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }

        else:

            payload = {

                "booking_id":
                    getattr(
                        booking_data,
                        "event_id",
                        "pending",
                    ),

                "service":
                    getattr(
                        booking_data,
                        "service_type",
                        None,
                    ),

                "date":
                    getattr(
                        booking_data,
                        "date",
                        None,
                    ),

                "time":
                    getattr(
                        booking_data,
                        "time",
                        None,
                    ),

                "customer_name":
                    getattr(
                        booking_data,
                        "name",
                        None,
                    ),

                "contact":
                    getattr(
                        booking_data,
                        "contact",
                        None,
                    ),

                "email":
                    getattr(
                        booking_data,
                        "email",
                        None,
                    ),

                "confirmed":
                    getattr(
                        booking_data,
                        "confirmed",
                        True,
                    ),

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }

        # =================================================
        # SEND REQUEST
        # =================================================

        last_error = None

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:

                response = requests.post(

                    self.webhook_url,

                    json=payload,

                    timeout=self.TIMEOUT,

                    headers={
                        "Content-Type":
                            "application/json"
                    },
                )

                response.raise_for_status()

                logger.info(
                    f"Webhook delivered "
                    f"(attempt {attempt}) "
                    f"status="
                    f"{response.status_code}"
                )

                return True

            except requests.Timeout as e:

                logger.warning(
                    f"Webhook timeout "
                    f"(attempt {attempt}): "
                    f"{e}"
                )

                last_error = e

            except requests.RequestException as e:

                logger.error(
                    f"Webhook request failed "
                    f"(attempt {attempt}): "
                    f"{e}"
                )

                last_error = e

        logger.error(
            f"Webhook delivery failed "
            f"after "
            f"{self.MAX_RETRIES} attempts."
        )

        raise RuntimeError(
            f"Webhook delivery failed: "
            f"{last_error}"
        )

    # =====================================================
    # BACKWARD COMPATIBILITY
    # =====================================================

    def send(
        self,
        booking_data,
    ):

        return self.send_notification(
            booking_data
        )