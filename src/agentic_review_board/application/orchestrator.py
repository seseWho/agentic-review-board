from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.execution import (
    Review,
    ReviewError,
    ReviewErrorKind,
    StageIdentity,
)
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.participants.analyst import Analyst, AnalystOutputError
from agentic_review_board.participants.risk_reviewer import (
    RiskReviewer,
    RiskReviewerOutputError,
)
from agentic_review_board.participants.solution_architect import (
    SolutionArchitect,
    SolutionArchitectOutputError,
)


class ReviewOrchestrator:
    """Executes the currently implemented review stages in explicit dependency order."""

    def __init__(
        self,
        analyst: Analyst,
        solution_architect: SolutionArchitect,
        risk_reviewer: RiskReviewer,
    ) -> None:
        self._analyst = analyst
        self._solution_architect = solution_architect
        self._risk_reviewer = risk_reviewer

    def execute(self, created_review: Review) -> Review:
        review = created_review.start()

        review = review.start_analyst()
        try:
            problem_analysis = self._analyst.analyze(review.review_input)
        except AnalystOutputError:
            return review.fail_analyst(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Analyst output validation failed",
                )
            )
        except Exception:
            return review.fail_analyst(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Analyst execution failed",
                )
            )
        review = review.complete_analyst(problem_analysis)

        review = review.start_solution_architect()
        analyst_stage = review.stage(StageIdentity.ANALYST)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError("completed Analyst stage must expose trusted ProblemAnalysis")
        try:
            solution_alternatives = self._solution_architect.propose(
                review.review_input,
                analyst_stage.output,
            )
        except SolutionArchitectOutputError:
            return review.fail_solution_architect(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Solution Architect output validation failed",
                )
            )
        except Exception:
            return review.fail_solution_architect(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Solution Architect execution failed",
                )
            )
        review = review.complete_solution_architect(solution_alternatives)

        review = review.start_risk_reviewer()
        analyst_stage = review.stage(StageIdentity.ANALYST)
        architect_stage = review.stage(StageIdentity.SOLUTION_ARCHITECT)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError("completed Analyst stage must expose trusted ProblemAnalysis")
        if not isinstance(architect_stage.output, SolutionAlternatives):
            raise ValueError(
                "completed Solution Architect stage must expose trusted SolutionAlternatives"
            )
        try:
            risk_assessment = self._risk_reviewer.assess(
                review.review_input,
                analyst_stage.output,
                architect_stage.output,
            )
        except RiskReviewerOutputError:
            return review.fail_risk_reviewer(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Risk Reviewer output validation failed",
                )
            )
        except Exception:
            return review.fail_risk_reviewer(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Risk Reviewer execution failed",
                )
            )
        return review.complete_risk_reviewer(risk_assessment)
