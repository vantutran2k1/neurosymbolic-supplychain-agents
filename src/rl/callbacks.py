from stable_baselines3.common.callbacks import BaseCallback


class ViolationTrackingCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(ViolationTrackingCallback, self).__init__(verbose)
        self.violations = 0
        self.episodes = 0

    def _on_step(self) -> bool:
        infos = self.locals["infos"]
        for info in infos:
            if "violation" in info:
                self.violations += 1

        if self.locals["dones"][0]:
            self.episodes += 1
            self.logger.record(
                "custom/violation_rate", self.violations / max(1, self.episodes)
            )
        return True
