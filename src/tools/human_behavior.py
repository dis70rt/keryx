import asyncio
import random


async def simulated_mouse_move(page) -> None:
    """Simulate realistic non-linear mouse movements to evade bot detection."""
    start_x = random.randint(100, 800)
    start_y = random.randint(100, 500)
    target_x = random.randint(200, 900)
    target_y = random.randint(200, 800)

    steps = random.randint(10, 20)
    for i in range(steps):
        t = i / steps
        current_x = start_x + (target_x - start_x) * t + random.uniform(-15, 15)
        current_y = start_y + (target_y - start_y) * t + random.uniform(-15, 15)
        await page.mouse.move(current_x, current_y)
        await asyncio.sleep(random.uniform(0.01, 0.05))

    await page.mouse.move(target_x, target_y)


async def human_scroll(page, max_scrolls: int = 5) -> None:
    """Progressive scroll to trigger lazy loading and mimic human reading."""
    try:
        total_height = await page.evaluate("document.body.scrollHeight")
    except Exception:
        total_height = 3000

    current_scroll = 0
    scroll_count = 0

    while current_scroll < total_height and scroll_count < max_scrolls:
        scroll_step = random.randint(400, 800)
        current_scroll += scroll_step
        scroll_count += 1

        await simulated_mouse_move(page)
        await page.mouse.wheel(delta_x=0, delta_y=scroll_step)
        await asyncio.sleep(random.uniform(1.0, 2.5))

        try:
            new_height = await page.evaluate("document.body.scrollHeight")
            total_height = new_height
        except Exception:
            pass
