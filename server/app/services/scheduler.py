from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date


def check_overdue_tasks(app):
    """检查过期任务并更新状态"""
    with app.app_context():
        from app import db
        from app.models.task import Task
        today = date.today()
        overdue = Task.query.filter(
            Task.deadline < today,
            Task.status.in_(["pending", "in_progress"])
        ).all()
        for task in overdue:
            task.status = "overdue"
        if overdue:
            db.session.commit()


def init_scheduler(app):
    """初始化定时任务调度器"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_overdue_tasks,
        trigger="interval",
        hours=1,
        args=[app],
        id="check_overdue",
        replace_existing=True,
    )
    scheduler.start()
    # 启动时立即检查一次
    check_overdue_tasks(app)
    return scheduler
