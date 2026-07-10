class ViolationRuleEngine:
    """
    TVS-9: Combines speed (TVS-7) and red light (TVS-8) detectors.
    """
    def __init__(self, speed_estimator, red_light_detector, speed_limit_kmh):
        self.speed_est    = speed_estimator
        self.rl_detector  = red_light_detector
        self.speed_limit  = speed_limit_kmh
        self.events       = []

    # ── Main per-frame update ─────────────────────────────────────────────────

    def update(self, detections, signal, frame_num):
        """
        Call once per frame with the current detections and signal state.
        """
        new_events = []

        # --- Run sub-detectors ---
        speed_events = self.speed_est.process(detections, frame_num)
        rl_events    = self.rl_detector.process(detections, signal, frame_num)

        # Process and store events here...
        # (To be expanded in later chunks)
        
        return new_events