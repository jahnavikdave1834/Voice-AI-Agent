from dataclasses import (
    dataclass,
    field,
)

# =====================================================
# REQUIRED FIELDS
# =====================================================

REQUIRED_FIELDS = [

    "service_type",
    "date",
    "time",
    "name",
    "contact",
    "email",
]

# =====================================================
# FIELD LABELS
# =====================================================

FIELD_LABELS = {

    "service_type":
        "Service Type",

    "date":
        "Date",

    "time":
        "Time",

    "name":
        "Name",

    "contact":
        "Contact Number",

    "email":
        "Email Address",
}

# =====================================================
# QUESTIONS
# =====================================================

QUESTIONS = {

    "service_type":
        "What type of appointment would you like to book?",

    "date":
        "What date would you prefer?",

    "time":
        "What time would you prefer?",

    "name":
        "May I have your name?",

    "contact":
        "Please provide your contact number.",

    "email":
        "Please provide your email address.",
}


# =====================================================
# BOOKING STATE
# =====================================================

@dataclass
class BookingState:

    # =================================================
    # BOOKING DETAILS
    # =================================================

    service_type: str = None

    date: str = None

    time: str = None

    time_period: str = None

    name: str = None

    contact: str = None

    email: str = None

    # =================================================
    # BOOKING STATUS
    # =================================================

    confirmed: bool = False

    event_id: str = None

    ready_for_confirmation: bool = False

    # =================================================
    # CONVERSATION STATES
    # =================================================

    awaiting_confirmation: bool = False

    awaiting_update_decision: bool = False

    awaiting_update_field: bool = False

    awaiting_update_value: bool = False

    awaiting_slot_selection: bool = False

    # =================================================
    # UPDATE FIELD TRACKING
    # =================================================

    field_to_update: str = None

    # =================================================
    # TEMP STORAGE
    # =================================================

    pending_slots: dict = field(
        default_factory=dict
    )

    # =================================================
    # UPDATE FIELD
    # =================================================

    def update_field(

        self,

        field_name,

        value,

    ):

        allowed_fields = {

        "service_type",
        "date",
        "time",
        "name",
        "contact",
        "email",
        "time_period",
        }

        if field_name not in allowed_fields:

            return False


        setattr(
            self,
            field_name,
            value,
        )

        return True

    # =================================================
    # STORE PENDING SLOTS
    # =================================================

    def store_pending_slots(

        self,

        slots: dict,

    ):

        self.pending_slots.update(
            slots
        )

    # =================================================
    # CLEAR PENDING
    # =================================================

    def clear_pending_slots(self):

        self.pending_slots = {}

    # =================================================
    # COMMIT PENDING
    # =================================================

    def commit_pending_slots(self):

        for key, value in (
            self.pending_slots.items()
        ):

            setattr(
                self,
                key,
                value,
            )

        self.clear_pending_slots()

    # =================================================
    # GET MISSING FIELDS
    # =================================================

    def get_missing_fields(self):

        missing = []

        for field_name in REQUIRED_FIELDS:

            value = getattr(
                self,
                field_name,
            )

            if not value:

                missing.append(
                    field_name
                )

        return missing

    # =================================================
    # CHECK COMPLETE
    # =================================================

    def all_required_present(self):

        return (
            len(
                self.get_missing_fields()
            ) == 0
        )

    # =================================================
    # RESET
    # =================================================

    def reset(self):

        self.service_type = None

        self.date = None

        self.time = None

        self.time_period = None

        self.name = None

        self.contact = None

        self.email = None

        self.confirmed = False

        self.event_id = None

        self.ready_for_confirmation = False

        self.awaiting_confirmation = False

        self.awaiting_update_decision = False

        self.awaiting_update_field = False

        self.awaiting_update_value = False

        self.awaiting_slot_selection = False

        self.field_to_update = None

        self.pending_slots = {}

    # =================================================
    # TO DICT
    # =================================================

    def to_dict(self):

        return {

            "service_type":
                self.service_type,

            "date":
                self.date,

            "time":
                self.time,

            "time_period":
                self.time_period,

            "name":
                self.name,

            "contact":
                self.contact,

            "email":
                self.email,

            "confirmed":
                self.confirmed,

            "event_id":
                self.event_id,
        }

    # =================================================
    # CONFIRMED BOOKING DATA
    # =================================================

    def get_confirmed_booking_data(self):

        return {

            "service_type":
                self.service_type,

            "date":
                self.date,

            "time":
                self.time,

            "time_period":
                self.time_period,

            "name":
                self.name,

            "contact":
                self.contact,

            "email":
                self.email,

            "confirmed":
                self.confirmed,

            "event_id":
                self.event_id,
        }