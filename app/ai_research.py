"""
AI-powered research agent for meeting prep.
Uses Anthropic Claude with web search to research companies.
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import anthropic


class MeetingPrepResearcher:
    """AI agent that researches companies for meeting preparation."""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    def research_company(
        self,
        company_name: str,
        company_website: Optional[str] = None,
        company_industry: Optional[str] = None,
        internal_context: Optional[Dict] = None
    ) -> Dict:
        """
        Research a company and generate meeting prep brief.

        Args:
            company_name: Name of the company to research
            company_website: Company website URL (if known)
            company_industry: Industry category (if known)
            internal_context: Dict with internal data like:
                - opportunities: List of opportunities with this account
                - activities: Recent activities/interactions
                - contacts: Key contacts at the company
                - pipeline_value: Total pipeline value
                - last_contact_date: When we last contacted them

        Returns:
            Dict with research brief containing:
                - company_overview: What they do, services, specialties
                - recent_projects: Recent projects and news
                - key_people: Decision makers and contacts
                - opportunity_intel: What they might need from you
                - talking_points: Specific conversation starters
                - internal_history: Your past interactions
                - researched_at: Timestamp
                - sources: List of sources used
        """
        # Build context for the AI
        context_parts = [f"Company name: {company_name}"]

        if company_website:
            context_parts.append(f"Website: {company_website}")
        if company_industry:
            context_parts.append(f"Industry: {company_industry}")

        # Add internal context if provided
        internal_summary = ""
        if internal_context:
            internal_parts = []

            if internal_context.get('opportunities'):
                opps = internal_context['opportunities']
                internal_parts.append(f"We have {len(opps)} opportunities with them:")
                for opp in opps[:5]:  # Limit to 5 most recent
                    internal_parts.append(f"  - {opp['name']} (Stage: {opp['stage']}, Value: ${opp['value']:,.0f if opp['value'] else 0})")

            if internal_context.get('last_contact_date'):
                internal_parts.append(f"Last contact: {internal_context['last_contact_date']}")

            if internal_context.get('pipeline_value'):
                internal_parts.append(f"Total pipeline value: ${internal_context['pipeline_value']:,.0f}")

            if internal_context.get('activities'):
                recent = internal_context['activities'][:3]
                if recent:
                    internal_parts.append(f"Recent interactions:")
                    for act in recent:
                        internal_parts.append(f"  - {act['date']}: {act['type']} - {act['subject']}")

            if internal_context.get('contacts'):
                contacts = internal_context['contacts']
                if contacts:
                    internal_parts.append(f"Key contacts:")
                    for contact in contacts[:5]:
                        internal_parts.append(f"  - {contact['name']}, {contact['title'] or 'N/A'}")

            if internal_parts:
                internal_summary = "\n\nOur internal data:\n" + "\n".join(internal_parts)

        # Construct the research prompt
        prompt = f"""You are a sales research assistant for a construction company that specializes in low-voltage electrical work, data/communications infrastructure, and horizontal directional drilling (HDD).

I have a meeting coming up with this company and need to prepare:

{chr(10).join(context_parts)}{internal_summary}

Please research this company and provide a comprehensive meeting prep brief. Use web search to find:

1. **Company Overview**: What they do, their services, specialties, size, locations
2. **Recent Projects & News**: Recent completed projects, ongoing work, press releases, awards, expansions
3. **Key Decision Makers**: Names, titles, backgrounds of people I should know about (especially those involved in procurement, project management, or facilities)
4. **Pipeline & Upcoming Work**: Any public information about their upcoming projects or plans
5. **Opportunity Intel**: Based on what they do, what specific services might they need from us? (low-voltage, data/comm, security systems, HDD/underground utilities)

Then synthesize this into:
- A concise company overview (2-3 sentences)
- List of their recent/notable projects
- Key people to know
- Specific talking points for the meeting (reference their recent work, ask targeted questions)
- Potential opportunities where we could help them

Keep it practical and focused on helping me have an informed, productive conversation. Focus on construction-related intelligence."""

        try:
            # Call Claude with web search
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=4000,
                tools=[{
                    "type": "web_search_20241111",
                    "name": "web_search",
                    "display_results_to_user": False
                }],
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract text content and sources
            brief_text = ""
            sources = []

            for block in response.content:
                if block.type == "text":
                    brief_text += block.text
                elif block.type == "web_search":
                    # Extract search results as sources
                    if hasattr(block, 'results'):
                        for result in block.results:
                            if hasattr(result, 'url') and hasattr(result, 'title'):
                                sources.append({
                                    'url': result.url,
                                    'title': result.title
                                })

            # Parse the AI response into structured sections
            brief = self._parse_brief(brief_text)
            brief['sources'] = sources[:10]  # Limit to 10 sources
            brief['researched_at'] = datetime.utcnow().isoformat()
            brief['company_name'] = company_name

            # Add internal context to the brief
            if internal_summary:
                brief['internal_history'] = internal_summary

            return brief

        except Exception as e:
            # Fallback if API call fails
            return {
                'error': str(e),
                'company_name': company_name,
                'company_overview': f"Unable to research {company_name} at this time.",
                'recent_projects': [],
                'key_people': [],
                'opportunity_intel': "",
                'talking_points': [],
                'internal_history': internal_summary or "",
                'sources': [],
                'researched_at': datetime.utcnow().isoformat()
            }

    def _parse_brief(self, text: str) -> Dict:
        """Parse AI response text into structured sections."""
        # Basic parsing - split by common section headers
        sections = {
            'company_overview': '',
            'recent_projects': [],
            'key_people': [],
            'opportunity_intel': '',
            'talking_points': [],
            'raw_content': text  # Keep full text for display
        }

        # Simple section extraction (can be improved with better parsing)
        lines = text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            line_lower = line.lower().strip()

            # Detect section headers
            if 'company overview' in line_lower or 'overview' in line_lower and line.startswith('#'):
                if current_section and current_content:
                    self._add_to_section(sections, current_section, current_content)
                current_section = 'company_overview'
                current_content = []
            elif 'recent project' in line_lower or 'notable project' in line_lower:
                if current_section and current_content:
                    self._add_to_section(sections, current_section, current_content)
                current_section = 'recent_projects'
                current_content = []
            elif 'key people' in line_lower or 'decision maker' in line_lower:
                if current_section and current_content:
                    self._add_to_section(sections, current_section, current_content)
                current_section = 'key_people'
                current_content = []
            elif 'opportunity' in line_lower or 'potential' in line_lower and 'opportunit' in line_lower:
                if current_section and current_content:
                    self._add_to_section(sections, current_section, current_content)
                current_section = 'opportunity_intel'
                current_content = []
            elif 'talking point' in line_lower or 'conversation' in line_lower:
                if current_section and current_content:
                    self._add_to_section(sections, current_section, current_content)
                current_section = 'talking_points'
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Add last section
        if current_section and current_content:
            self._add_to_section(sections, current_section, current_content)

        return sections

    def _add_to_section(self, sections: Dict, section_name: str, content: List[str]):
        """Helper to add parsed content to appropriate section."""
        text = '\n'.join(content).strip()

        if section_name in ['recent_projects', 'key_people', 'talking_points']:
            # Parse bullet points
            items = []
            for line in content:
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    items.append(line.lstrip('-•* ').strip())
            sections[section_name] = items if items else [text]
        else:
            sections[section_name] = text
