from pug_scheduler import PugScheduler
from start_pug import StartPug

active_start_pug: StartPug | None = None
active_pug_scheduler: PugScheduler | None = None

early_start_pug: StartPug | None = None
early_pug_scheduler: PugScheduler | None = None

startup = True


def change_active_pug():
    global active_start_pug, active_pug_scheduler
    active_start_pug = early_start_pug
    active_pug_scheduler = early_pug_scheduler
