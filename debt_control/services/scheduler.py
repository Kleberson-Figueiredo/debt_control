from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from debt_control.database import engine
from debt_control.services.notification_service import notify_installments


def start_scheduler():  # pragma: no cover
    scheduler = BackgroundScheduler()

    def job_notify():
        session = Session(engine)
        try:
            notify_installments(session)
        finally:
            session.close()

    scheduler.add_job(job_notify, 'cron', hour=20, minute=00)
    scheduler.start()
