from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.execution import Review, StageIdentity
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.solution_architect import SolutionArchitect


class ReviewOrchestrator:
    """Executes the currently implemented review stages in explicit dependency order."""

    def __init__(
        self,
        analyst: Analyst,
        solution_architect: SolutionArchitect,
    ) -> None:
        self._analyst = analyst
        self._solution_architect = solution_architect

    def execute(self, created_review: Review) -> Review:
        review = created_review.start()

        review = review.start_analyst()
        problem_analysis = self._analyst.analyze(review.review_input)
        review = review.complete_analyst(problem_analysis)

        review = review.start_solution_architect()
        analyst_stage = review.stage(StageIdentity.ANALYST)
        if not isinstance(analyst_stage.output, ProblemAnalysis):
            raise ValueError("completed Analyst stage must expose trusted ProblemAnalysis")
        solution_alternatives = self._solution_architect.propose(
            review.review_input,
            analyst_stage.output,
        )
        review = review.complete_solution_architect(solution_alternatives)

        return review
