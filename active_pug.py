import main.pug_scheduler
import main.start_pug

import second.pug_scheduler
import second.start_pug

pug_scheduler = None
start_pug = None

early_start_pug = None
early_pug_scheduler = None


async def change_active_pug(active_pug):
    global pug_scheduler, start_pug
    if active_pug == 'main':
        pug_scheduler = main.pug_scheduler
        start_pug = main.start_pug
    elif active_pug == 'second':
        pug_scheduler = second.pug_scheduler
        start_pug = second.start_pug


async def change_early_active_pug(active_pug):
    global early_start_pug, early_pug_scheduler
    if active_pug == 'main':
        early_start_pug = main.start_pug
        early_pug_scheduler = main.pug_scheduler
    elif active_pug == 'second':
        early_start_pug = second.start_pug
        early_pug_scheduler = second.pug_scheduler
