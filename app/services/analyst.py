"""
Stage: Gemini Analyst
Ranked candidates + project context -> final human-readable site report (markdown).
"""
import json

SYSTEM_PROMPT = """You are the final analyst in a commercial site-selection platform.
You receive: the original project definition, the research strategy used, and a ranked list of
candidate sites with their scores. Write a clear, decision-ready report in markdown.

Structure your report as:
## Recommendation
One paragraph naming the top-ranked site (by id and address) and why it's the best choice.

## Top candidates compared
A short markdown table comparing the top 3 candidates: id, address, total score, and the single
biggest strength and biggest weakness of each.

## Risks & caveats
2-4 bullet points on what could not be captured by this data (e.g. rent prices, foot traffic
counts, zoning) and what the user should verify on the ground before committing.

## Next steps
2-3 concrete, practical next actions.

Be concise, specific, and reference actual numbers from the data you were given. Do not invent
data that wasn't provided. Respond with markdown only, no surrounding commentary.
"""


def generate_report(vertex_client, project_definition: dict, research_strategy: dict, ranked_candidates: list) -> str:
    user_prompt = (
        f"Project definition:\n{json.dumps(project_definition, indent=2)}\n\n"
        f"Research strategy:\n{json.dumps(research_strategy, indent=2)}\n\n"
        f"Ranked candidates:\n{json.dumps(ranked_candidates, indent=2)}"
    )
    return vertex_client.generate_text(SYSTEM_PROMPT, user_prompt)
