import asyncio
from . import TaskService, SettingService
from ..utils import logger


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
        args = {"_": [settings["capturing"]['laser.current']]}
        tid = await self.task_service.create_script_task(
            "lasercontrol", None, **args)
        return tid

    async def start_pzt(self) -> str:
        settings = await self.setting_service.get()
        tid = await self.task_service.create_script_task(
            "pztcontrol",
            None,
            _=[
                settings['capturing']['pzt.freq'],
                settings['capturing']['pzt.voltage'],
            ])
        return tid

    async def control_mfs_pump(self, action: str):
        assert action[-2] in list('sb')
        assert action[-1] in list('fr')
        settings = await self.setting_service.get()

        try:
            tid = await self.task_service.create_script_task(
                'mfspumpcontrol',
                None,
                _=[
                    action,
                    settings['capturing']['mfs.speed'],
                ])
            return await self.task_service.get(tid)
        except asyncio.CancelledError as e:
            logger.warning(f'cancel control_mfs_pump task {action=}')
            try:
                await self.task_service.run_script('mfspumpcontrol', 'stop')
                raise e
            except Exception as stop_err:
                logger.error(f'fail to stop mfs pump script：{stop_err}')
                raise stop_err

    async def control_syringe_pump(self, action: str):
        assert action in ["infuse", "withdraw"], f"{action=} is invalid"
        settings = await self.setting_service.get()
        try:
            tid = await self.task_service.create_script_task(
                "spcontrol",
                None,
                _=[
                    action, settings['capturing']['syringe.flow'],
                    settings['capturing']['syringe.volume']
                ])
            return await self.task_service.get(tid)
        except asyncio.CancelledError as e:
            logger.warning(f'cancel control_syringe_pump task {action=}')
            try:
                await self.task_service.run_script('spcontrol', 'stop')
                raise e
            except Exception as stop_err:
                logger.error(f'fail to stop syringe pump script：{stop_err}')
                raise stop_err

    async def clean(self, action: str) -> str:
        return await self.task_service.create_script_task(action)