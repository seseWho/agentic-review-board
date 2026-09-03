from agentic_review_board.application.observation import ReviewObserver
from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    Review,
    ReviewError,
    ReviewErrorKind,
    StageIdentity,
)
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.participants.analyst import Analyst, AnalystOutputError
from agentic_review_board.participants.coordinator import (
    Coordinator,
    CoordinatorOutputError,
)
from agentic_review_board.participants.critic import Critic, CriticOutputError
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
        critic: Critic,
        coordinator: Coordinator,
    ) -> None:
        self._analyst = analyst
        self._solution_architect = solution_architect
        self._risk_reviewer = risk_reviewer
        self._critic = critic
        self._coordinator = coordinator

    def execute(
        self,
        created_review: Review,
        *,
        observer: ReviewObserver | None = None,
    ) -> Review:
        review = created_review.start()
        self._notify(observer, review)

        review = review.start_analyst()
        self._notify(observer, review)
        try:
            problem_analysis = self._analyst.analyze(review.review_input)
        except AnalystOutputError:
            review = review.fail_analyst(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Analyst output validation failed",
                )
            )
            self._notify(observer, review)
            return review
        except Exception:
            review = review.fail_analyst(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Analyst execution failed",
                )
            )
            self._notify(observer, review)
            return review
        review = review.complete_analyst(problem_analysis)
        self._notify(observer, review)

        review = review.start_solution_architect()
        self._notify(observer, review)
        analyst_stage = review.stage(StageIdentity.ANALYST)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError("completed Analyst stage must expose trusted ProblemAnalysis")
        try:
            solution_alternatives = self._solution_architect.propose(
                review.review_input,
                analyst_stage.output,
            )
        except SolutionArchitectOutputError:
            review = review.fail_solution_architect(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Solution Architect output validation failed",
                )
            )
            self._notify(observer, review)
            return review
        except Exception:
            review = review.fail_solution_architect(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Solution Architect execution failed",
                )
            )
            self._notify(observer, review)
            return review
        review = review.complete_solution_architect(solution_alternatives)
        self._notify(observer, review)

        review = review.start_risk_reviewer()
        self._notify(observer, review)
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
            review = review.fail_risk_reviewer(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Risk Reviewer output validation failed",
                )
            )
            self._notify(observer, review)
            return review
        except Exception:
            review = review.fail_risk_reviewer(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Risk Reviewer execution failed",
                )
            )
            self._notify(observer, review)
            return review
        review = review.complete_risk_reviewer(risk_assessment)
        self._notify(observer, review)

        review = review.start_critic()
        self._notify(observer, review)
        analyst_stage = review.stage(StageIdentity.ANALYST)
        architect_stage = review.stage(StageIdentity.SOLUTION_ARCHITECT)
        reviewer_stage = review.stage(StageIdentity.RISK_REVIEWER)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError("completed Analyst stage must expose trusted ProblemAnalysis")
        if not isinstance(architect_stage.output, SolutionAlternatives):
            raise ValueError(
                "completed Solution Architect stage must expose trusted SolutionAlternatives"
            )
        if not isinstance(reviewer_stage.output, RiskAssessment):
            raise ValueError(
                "completed Risk Reviewer stage must expose trusted RiskAssessment"
            )
        try:
            critical_review = self._critic.review(
                review.review_input,
                analyst_stage.output,
                architect_stage.output,
                reviewer_stage.output,
            )
        except CriticOutputError:
            review = review.fail_critic(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Critic output validation failed",
                )
            )
            self._notify(observer, review)
            return review
        except Exception:
            review = review.fail_critic(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Critic execution failed",
                )
            )
            self._notify(observer, review)
            return review
        review = review.complete_critic(critical_review)
        self._notify(observer, review)

        review = review.start_coordinator()
        self._notify(observer, review)
        analyst_stage = review.stage(StageIdentity.ANALYST)
        architect_stage = review.stage(StageIdentity.SOLUTION_ARCHITECT)
        reviewer_stage = review.stage(StageIdentity.RISK_REVIEWER)
        critic_stage = review.stage(StageIdentity.CRITIC)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError(
                "completed Analyst stage must expose trusted ProblemAnalysis"
            )
        if not isinstance(architect_stage.output, SolutionAlternatives):
            raise ValueError(
                "completed Solution Architect stage must expose trusted SolutionAlternatives"
            )
        if not isinstance(reviewer_stage.output, RiskAssessment):
            raise ValueError(
                "completed Risk Reviewer stage must expose trusted RiskAssessment"
            )
        if not isinstance(critic_stage.output, CriticalReview):
            raise ValueError("completed Critic stage must expose trusted CriticalReview")
        try:
            final_review = self._coordinator.coordinate(
                review.review_input,
                analyst_stage.output,
                architect_stage.output,
                reviewer_stage.output,
                critic_stage.output,
            )
        except CoordinatorOutputError:
            review = review.fail_coordinator(
                ReviewError(
                    kind=ReviewErrorKind.OUTPUT_VALIDATION,
                    message="Coordinator output validation failed",
                )
            )
            self._notify(observer, review)
            return review
        except Exception:
            review = review.fail_coordinator(
                ReviewError(
                    kind=ReviewErrorKind.EXECUTION,
                    message="Coordinator execution failed",
                )
            )
            self._notify(observer, review)
            return review
        review = review.complete_coordinator(final_review)
        self._notify(observer, review)
        return review

    @staticmethod
    def _notify(observer: ReviewObserver | None, review: Review) -> None:
        if observer is not None:
            observer(review)
