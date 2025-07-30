import enum

class QuestionStatus(enum.Enum):
    """Enumeration for question processing status"""
    PENDING = "pending"
    ANSWERED = "answered"
    ERROR = "error"
