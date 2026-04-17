import math

class OneEuroFilter:
    def __init__(self, freq=120.0, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev = None
        self._dx_prev = None
        self._t_prev = None

    @staticmethod
    def _alpha(cutoff, freq):
        if freq == 0:
            return 1.0
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau * freq)

    def _low_pass_filter(self, value, prev_value, alpha):
        if prev_value is None:
            return value
        return alpha * value + (1.0 - alpha) * prev_value

    def __call__(self, timestamp, value):
        if self._t_prev is None:
            self._t_prev = timestamp
            self._x_prev = value
            self._dx_prev = 0.0
            return value

        dt = timestamp - self._t_prev
        if dt == 0:
            return self._x_prev

        self.freq = 1.0 / dt
        dx = (value - self._x_prev) / dt

        alpha_d = self._alpha(self.d_cutoff, self.freq)
        dx_filtered = self._low_pass_filter(dx, self._dx_prev, alpha_d)

        effective_cutoff = self.min_cutoff + self.beta * abs(dx_filtered)
        alpha_x = self._alpha(effective_cutoff, self.freq)
        x_filtered = self._low_pass_filter(value, self._x_prev, alpha_x)

        self._x_prev = x_filtered
        self._dx_prev = dx_filtered
        self._t_prev = timestamp

        return x_filtered
