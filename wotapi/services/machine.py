import asyncio
from . import TaskService, SettingService


class MachineService:
    """
    Control machines
    """
    def __init__(self, task_service: TaskService,
                 setting_service: SettingService):
        self.task_service = task_service
        self.setting_service = setting_service

    async def start_laser(self) -> str:
        settings = await self.setting_service.get()
        args = {"LASER": settings["LASER"]}
        tid = await self.task_service.create_script_task(
            "lasercontrol", None, **args)
        return tid

    async def start_pzt(self) -> str:
        settings = await self.setting_service.get()
        args = {"PZ3": ",".join([str(v) for v in settings.get("CPZT")])}
        tid = await self.task_service.create_script_task(
            "pzcontrol", None, **args)
        return tid

    async def control_syringe_pump(self, action: str) -> str:
        assert action in ["infuse", "withdraw",
                          "stop"], f"{action=} is invalid"
        settings = await self.setting_service.get()
        args = {"__SINGLE": [action]}
        if action in ["infuse", "withdraw"]:
            args["__SINGLE"].extend(settings["SPV"])
        tid = await self.task_service.create_script_task(
            "spcontrol", None, **args)
        return tid

    async def clean(self, action: str) -> str:
        queue = asyncio.Queue()
        tid = await self.task_service.create_script_task(action, queue)
        return tid