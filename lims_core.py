from lims_enums import AnalysisStatus, SampleStatus, SampleType

class Analysis:
    """Repræsenterer en standard kemisk eller mikrobiologisk test."""
    def __init__(self, name: str, lower_limit: float, upper_limit: float, decimals: int = 1):
        self.name = name
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.decimals = decimals
        self._result = None
        self.status = AnalysisStatus.PENDING

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value: float):
        if value < 0:
            raise ValueError("Et analyseresultat kan ikke være negativt!")
        self._result = round(value, self.decimals)
        self._evaluate()

    def _evaluate(self):
        if self.lower_limit <= self._result <= self.upper_limit:
            self.status = AnalysisStatus.PASSED
        else:
            self.status = AnalysisStatus.OOS

class SpectroAnalysis(Analysis):
    """Arv: En to-komponent spektrofotometrisk analyse (Bølgelængde + % Koncentration)."""
    def __init__(self, name: str, lower_limit: float, upper_limit: float, expected_wavelength: int):
        super().__init__(name, lower_limit, upper_limit, decimals=3)
        self.expected_wavelength = expected_wavelength
        self.measured_wavelength = None

    @property
    def concentration(self):
        return self.result

    @concentration.setter
    def concentration(self, value: float):
        self.result = value

class Sample:
    """Repræsenterer en laboratorreprøve med differentierede testprogrammer."""
    def __init__(self, sample_id: str, sample_type: SampleType):
        self.sample_id = sample_id
        self.sample_type = sample_type
        self.analyses = []  # HER VAR FEJLEN: Nu initialiseres listen korrekt
        self.status = SampleStatus.REGISTERED
        self._assign_testing_program()

    def _assign_testing_program(self):
        """Tildeler automatisk de korrekte specifikke analyser ud fra produktkategori."""
        if self.sample_type == SampleType.RM:
            self.analyses.append(Analysis("pH", 6.5, 7.5, decimals=2))
            self.analyses.append(Analysis("Renhed", 98.0, 100.0, decimals=1))
        
        elif self.sample_type == SampleType.DS:
            self.analyses.append(Analysis("pH", 6.5, 7.5, decimals=2))
            self.analyses.append(Analysis("Renhed", 98.0, 100.0, decimals=1))
            self.analyses.append(SpectroAnalysis("UV-Vis Abs", 90.000, 100.000, expected_wavelength=540))
            
        elif self.sample_type == SampleType.DP:
            self.analyses.append(Analysis("Renhed", 98.0, 100.0, decimals=1))
            self.analyses.append(SpectroAnalysis("UV-Vis Abs", 90.000, 100.000, expected_wavelength=540))
            
        elif self.sample_type == SampleType.IHR:
            self.analyses.append(Analysis("pH", 6.5, 7.5, decimals=2))
            self.analyses.append(Analysis("Renhed", 98.0, 100.0, decimals=1))
            self.analyses.append(SpectroAnalysis("UV-Vis Abs", 90.000, 100.000, expected_wavelength=540))

    def add_analysis(self, analysis: Analysis):
        self.analyses.append(analysis)

    def remove_analysis(self, analysis_name: str) -> bool:
        for index, ana in enumerate(self.analyses):
            if ana.name.upper() == analysis_name.upper():
                del self.analyses[index]
                self.evaluate_sample()
                return True
        return False

    def evaluate_sample(self):
        if not self.analyses:
            self.status = SampleStatus.REGISTERED
            return

        statuses = [ana.status for ana in self.analyses]

        if AnalysisStatus.OOS in statuses:
            self.status = SampleStatus.REJECTED
        elif AnalysisStatus.PENDING in statuses:
            self.status = SampleStatus.IN_PROGRESS
        else:
            self.status = SampleStatus.APPROVED

    def sort_analyses(self):
        self.analyses.sort(key=lambda x: x.name)
