"""Algorithmic pre-cleaner for raw scraped LinkedIn text.

Strips LinkedIn UI chrome, sidebar noise, duplicate headers, reaction
counters, "More profiles for you" blocks, etc. — reducing the payload
sent to the LLM by 60-80% without losing any profile-relevant content.
"""

import re


# ── Patterns that appear verbatim and carry zero profile value ──────
_JUNK_LINES: list[str] = [
    "0 notifications",
    "Skip to main content",
    "Skip to search",
    "Keyboard shortcuts",
    "Close jump menu",
    "All activity",
    "Loaded",
    "Show all",
    "Show more",
    "Show credential",
    "Show publication",
    "Show more results",
    "… more",
    "…more",
    "Visit my website",
    "Profile enhanced with Premium",
    "LinkedIn helped me get this job",
    "helped me get this job",
    "Explore Premium profiles",
    "You might like",
    "Pages for you",
    "People you may know",
    "More profiles for you",
]

# Lines that exactly match these are dropped
_EXACT_DROP: set[str] = {
    "More", "Follow", "Message", "Connect", "Like", "Comment",
    "Repost", "Send", "Posts", "Comments", "Images", "Reactions",
    "Top Voices", "Companies", "Groups", "Newsletters", "Schools",
    "Interests", "·", "•",
}

# ── Regex patterns for noisy content ───────────────────────────────
_NOISE_PATTERNS: list[re.Pattern] = [
    # Reaction/engagement counters: "15 reactions", "2 comments", "3 reposts"
    re.compile(r"^\d[\d,]* (?:reactions?|comments?|reposts?|endorsements?)$", re.IGNORECASE),
    # Standalone numbers (reaction counts rendered alone)
    re.compile(r"^[\d,]+$"),
    # "Feed post number N" markers
    re.compile(r"^Feed post number \d+$", re.IGNORECASE),
    # Timestamps duplicated: "22 hours ago • Visible to anyone..."
    re.compile(r"^\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago\s*[•·]?\s*(?:Edited\s*[•·]?\s*)?(?:Visible to anyone.*)?$", re.IGNORECASE),
    # Connection degree markers: "· 3rd+", "• 3rd+"
    re.compile(r"^[·•]\s*(?:1st|2nd|3rd)\+?$"),
    # "Premium • 3rd+" markers
    re.compile(r"^Premium\s*[·•]\s*(?:1st|2nd|3rd)\+?$", re.IGNORECASE),
    # Follower counts: "3,120 followers", "4,162,601 followers"
    re.compile(r"^[\d,]+\s+followers?$", re.IGNORECASE),
    # Credential IDs
    re.compile(r"^Credential ID\s+\S+$", re.IGNORECASE),
    # "Activate to view larger image" accessibility tags
    re.compile(r"^Activate to view larger image", re.IGNORECASE),
    # "Starting a new position" / "Starting a New Position"
    re.compile(r"^Starting a [Nn]ew [Pp]osition$"),
    # LinkedIn shortened links on their own line
    re.compile(r"^https?://lnkd\.in/\S+$"),
    # Hashtag-only lines: "hashtag\n#meta"
    re.compile(r"^hashtag$", re.IGNORECASE),
    re.compile(r"^#\w+$"),
    # Endorsement noise: "Endorsed by X and N others..."
    re.compile(r"^Endorsed by .+", re.IGNORECASE),
    # "Endorse" count lines: "1 endorsement", "46 endorsements"
    re.compile(r"^\d+\s+endorsements?$", re.IGNORECASE),
    # Skill association lines within Skills section
    re.compile(r"^\d+ experiences? at .+", re.IGNORECASE),
    # "Other authors" / "Other contributors"
    re.compile(r"^Other (?:authors|contributors)$", re.IGNORECASE),
]

# ── Block-level sections we want to remove entirely ────────────────
_BLOCK_START_MARKERS: list[str] = [
    "More profiles for you",
    "People you may know",
    "Explore Premium profiles",
    "You might like",
    "Pages for you",
]

# Markers that start blocks to strip within the Main Profile page.
# Everything from these markers to the next major section header is dropped.
_MAIN_PROFILE_CUT_MARKERS: list[str] = [
    "Causes",
    "Recommendations",
]


def _is_noise_line(line: str) -> bool:
    """Return True if *line* is LinkedIn UI noise."""
    stripped = line.strip()
    if not stripped:
        return False  # blank lines handled separately

    # Exact match drops
    if stripped in _EXACT_DROP:
        return True

    # Junk prefix match
    for junk in _JUNK_LINES:
        if stripped == junk or stripped.startswith(junk):
            return True

    # Regex pattern match
    for pat in _NOISE_PATTERNS:
        if pat.match(stripped):
            return True

    return False


def _remove_sidebar_blocks(text: str) -> str:
    """Cut everything after sidebar markers like 'More profiles for you'."""
    for marker in _BLOCK_START_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    return text


def _collapse_repeated_headers(text: str) -> str:
    """Remove repeated profile header blocks that LinkedIn injects on every section page."""
    # Pattern: the person's name + headline repeated multiple times
    lines = text.split("\n")
    seen_header_blocks: dict[str, int] = {}
    cleaned: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect "Akash Borate Premium Profile 3rd+" style repeated headers
        if "Premium Profile" in line and "3rd+" in line:
            # Skip this line and the next few lines that form the repeated header
            # (name, headline, "Visit my website", timestamp)
            j = i + 1
            while j < len(lines) and j < i + 8:
                next_line = lines[j].strip()
                if next_line and not _is_noise_line(next_line) and len(next_line) > 60:
                    # Looks like actual post content — stop skipping
                    break
                j += 1
            i = j
            continue

        cleaned.append(lines[i])
        i += 1

    return "\n".join(cleaned)


def _collapse_blank_lines(text: str) -> str:
    """Replace 3+ consecutive blank lines with a single blank line."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _deduplicate_sections(sections: dict[str, str]) -> dict[str, str]:
    """Remove sections that are fully contained in 'Main Profile'.

    The Main Profile page already includes Experience, Education, Skills,
    etc. in abbreviated form, but the dedicated sub-pages have richer data.
    We keep the sub-pages and drop the Contact Info duplicate (which is
    almost always a carbon copy of Main Profile).
    """
    cleaned = dict(sections)

    # Contact Info is nearly always a full duplicate of Main Profile
    if "Contact Info" in cleaned and "Main Profile" in cleaned:
        # Only keep Contact Info if it has unique short content (actual contact details)
        ci_text = cleaned["Contact Info"]
        mp_text = cleaned["Main Profile"]
        # If Contact Info is >80% the size of Main Profile, it's a duplicate
        if len(ci_text) > len(mp_text) * 0.7:
            del cleaned["Contact Info"]

    return cleaned


def _truncate_posts(text: str, max_posts: int = 5, max_chars_per_post: int = 600) -> str:
    """Truncate the Recent Posts section to keep only the most relevant content.

    Each post is capped at *max_chars_per_post* characters and only the
    first *max_posts* posts are kept.
    """
    # Split on common post delimiters
    # Posts typically start with the person's name repeated
    post_blocks = re.split(r"\n(?=\d+[wh]\s*[•·]|\d+\s*(?:week|month|year|hour|day)s?\s*(?:ago)?)", text)

    if len(post_blocks) <= 1:
        # Try alternate split: numbered feed posts
        post_blocks = re.split(r"\n(?=Feed post number \d+)", text)

    if len(post_blocks) <= 1:
        # Fallback: just truncate the whole section
        return text[:max_posts * max_chars_per_post]

    kept = post_blocks[:max_posts + 1]  # +1 for the header block
    truncated = []
    for block in kept:
        if len(block) > max_chars_per_post:
            truncated.append(block[:max_chars_per_post] + "\n[... truncated]")
        else:
            truncated.append(block)

    return "\n".join(truncated)


def _strip_activity_from_main_profile(text: str) -> str:
    """Remove the Activity/posts block from the Main Profile section.

    The Main Profile page embeds the person's recent posts inline, but
    we already scrape them separately in the "Recent Posts" section.
    Keeping both roughly doubles the token cost for no new information.
    """
    # The Activity block starts with a line like "Activity" or "\nActivity\n"
    # and runs until the next major section like "Experience"
    activity_start = None
    activity_end = None

    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "Activity" and activity_start is None:
            activity_start = i
        elif activity_start is not None and stripped in (
            "Experience", "Education", "Skills", "Projects",
            "Licenses & certifications", "Certifications",
            "Publications", "Honors & awards", "Languages",
            "Organizations", "Courses",
        ):
            activity_end = i
            break

    if activity_start is not None:
        if activity_end is None:
            activity_end = len(lines)
        lines = lines[:activity_start] + lines[activity_end:]

    # Also strip Causes / Recommendations blocks
    text = "\n".join(lines)
    for marker in _MAIN_PROFILE_CUT_MARKERS:
        pattern = re.compile(
            rf"\n{re.escape(marker)}\n.*?(?=\n(?:Experience|Education|Skills|Projects|Licenses|Publications|Honors|Languages|Organizations|Courses|$))",
            re.DOTALL,
        )
        text = pattern.sub("", text)

    return text


def clean_section(section_name: str, raw_text: str) -> str:
    """Clean a single scraped section."""
    # Step 1: Remove sidebar "More profiles for you" blocks
    text = _remove_sidebar_blocks(raw_text)

    # Step 2: Remove repeated post headers (name + headline repeated per post)
    text = _collapse_repeated_headers(text)

    # Step 3: Line-by-line noise removal
    lines = text.split("\n")
    cleaned_lines = [line for line in lines if not _is_noise_line(line)]
    text = "\n".join(cleaned_lines)

    # Step 4: Strip Activity posts from Main Profile (already in Recent Posts)
    if section_name == "Main Profile":
        text = _strip_activity_from_main_profile(text)

    # Step 5: Truncate posts to avoid blowing up context
    if section_name == "Recent Posts":
        text = _truncate_posts(text, max_posts=5, max_chars_per_post=600)

    # Step 6: Collapse excessive blank lines
    text = _collapse_blank_lines(text)

    return text.strip()


def clean_scraped_data(raw_data: dict[str, str]) -> dict[str, str]:
    """Clean all sections of a scraped LinkedIn profile or company page.

    This is the main entry point.  Call it on the raw dict loaded from
    a snapshot JSON before feeding data to the LLM pipeline.

    Returns a new dict with the same keys but cleaned values.
    """
    # Step 0: Drop fully-duplicate sections
    data = _deduplicate_sections(raw_data)

    # Step 1: Clean each section individually
    cleaned: dict[str, str] = {}
    for section, text in data.items():
        result = clean_section(section, text)
        if result:  # drop empty sections
            cleaned[section] = result

    # Step 2: Aggressively truncate to fit within local LLM context limits (~10k chars)
    # Priority order for keeping data: Main Profile > Experience > Recent Posts > Education > Projects > others
    max_total_chars = 10000
    priority_keys = ["Main Profile", "Experience", "Recent Posts", "Education", "Skills", "Projects", "Certifications"]
    
    final_cleaned: dict[str, str] = {}
    current_chars = 0
    
    for key in priority_keys:
        if key in cleaned:
            text = cleaned[key]
            # If adding this entire section exceeds the limit, truncate the section
            if current_chars + len(text) > max_total_chars:
                allowed_chars = max_total_chars - current_chars
                if allowed_chars > 200:  # Only add if we have a reasonable chunk left
                    final_cleaned[key] = text[:allowed_chars] + "\n[... truncated for context limits]"
                break
            else:
                final_cleaned[key] = text
                current_chars += len(text)

    # Add any remaining keys that fit (rare, but just in case)
    for key, text in cleaned.items():
        if key not in final_cleaned and current_chars + len(text) <= max_total_chars:
            final_cleaned[key] = text
            current_chars += len(text)

    return final_cleaned
