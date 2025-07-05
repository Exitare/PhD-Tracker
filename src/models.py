from pydantic import BaseModel
from typing import Optional
from dataclasses import dataclass, field
from typing import List, Optional


class AIMilestone(BaseModel):
    milestone: str
    due_date: str
    id: int | None = None

    def __str__(self):
        return f"Milestone: {self.milestone}, Due Date: {self.due_date}, ID: {self.id}"

    def to_json(self):
        return {
            "milestone": self.milestone,
            "due_date": self.due_date,
            "id": self.id
        }


class AIJournalRecommendation(BaseModel):
    name: str
    scope: str
    impact_factor: Optional[float]
    open_access: bool
    link: str

    def __str__(self):
        return f"Journal: {self.name}, Scope: {self.scope}, Impact Factor: {self.impact_factor}, Open Access: {self.open_access}, Link: {self.link}"

    def to_json(self):
        return {
            "name": self.name,
            "scope": self.scope,
            "impact_factor": self.impact_factor,
            "open_access": self.open_access,
            "link": self.link
        }


@dataclass
class InitialSubmission:
    format: str = ""
    figures: str = ""
    line_numbers: bool = False
    figure_legends: str = ""
    reference_list_with_titles: bool = False


@dataclass
class Title:
    max_length_characters: Optional[int] = None
    max_length_words: Optional[int] = None
    requirements: str = ""


@dataclass
class Abstract:
    length_words: Optional[int] = None
    type: str = ""


@dataclass
class TitleAndAbstract:
    title: Title = field(default_factory=Title)
    abstract: Abstract = field(default_factory=Abstract)


@dataclass
class LengthWords:
    max: Optional[int] = None


@dataclass
class FiguresOrTables:
    max: Optional[int] = None


@dataclass
class References:
    max: Optional[int] = None
    methods_references_excluded: bool = False


@dataclass
class MainText:
    flexibility: str = ""
    length_words: LengthWords = field(default_factory=LengthWords)
    figures_or_tables: FiguresOrTables = field(default_factory=FiguresOrTables)
    references: References = field(default_factory=References)


@dataclass
class MethodsLengthWords:
    suggested_max: Optional[int] = None


@dataclass
class MethodsSection:
    replicability_required: bool = False
    length_words: MethodsLengthWords = field(default_factory=MethodsLengthWords)
    detailed_protocols: str = ""
    references_not_counted: bool = False


@dataclass
class InitialFigureSubmission:
    resolution: str = ""
    format: str = ""


@dataclass
class FinalFigureSubmission:
    resolution_dpi: Optional[int] = None
    color_mode: str = ""
    fonts: str = ""
    format: str = ""


@dataclass
class Tables:
    title_required: bool = False
    footnotes_required: bool = False
    page_fit_required: bool = False


@dataclass
class FiguresAndTables:
    initial_submission: InitialFigureSubmission = field(default_factory=InitialFigureSubmission)
    final_submission: FinalFigureSubmission = field(default_factory=FinalFigureSubmission)
    tables: Tables = field(default_factory=Tables)


@dataclass
class ReferenceSection:
    titles_required: bool = False
    numbering: str = ""
    main_text_limit: Optional[int] = None
    methods_exempt: bool = False


@dataclass
class EndMatter:
    author_contributions: bool = False
    competing_interests: bool = False
    data_availability_statement: bool = False
    code_availability_statement: bool = False
    acknowledgements: str = ""
    materials_correspondence: str = ""


@dataclass
class StatisticsAndReporting:
    tests_described: bool = False
    error_bars_defined: bool = False
    n_values_reported: bool = False
    p_values_and_test_stats_reported: bool = False
    reporting_summary_required_for_life_sciences: bool = False


@dataclass
class SubmissionRequirements:
    article_types: List[str] = field(default_factory=list)
    initial_submission: InitialSubmission = field(default_factory=InitialSubmission)
    title_and_abstract: TitleAndAbstract = field(default_factory=TitleAndAbstract)
    main_text: MainText = field(default_factory=MainText)
    methods_section: MethodsSection = field(default_factory=MethodsSection)
    figures_and_tables: FiguresAndTables = field(default_factory=FiguresAndTables)
    references: ReferenceSection = field(default_factory=ReferenceSection)
    end_matter: EndMatter = field(default_factory=EndMatter)
    statistics_and_reporting: StatisticsAndReporting = field(default_factory=StatisticsAndReporting)
    submission_checklist: List[str] = field(default_factory=list)
    source_url: str = ""
