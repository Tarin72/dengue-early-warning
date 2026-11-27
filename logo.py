"""Mosquito logo (inline SVG, no external files, works offline)."""

LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="96" height="96"
     role="img" aria-label="Mosquito logo">
  <circle cx="100" cy="100" r="94" fill="#FFB703"/>
  <circle cx="100" cy="100" r="94" fill="none" stroke="#FFFFFF" stroke-width="6"/>
  <!-- wings -->
  <ellipse cx="62" cy="70" rx="44" ry="17" transform="rotate(-32 62 70)"
           fill="#FFFFFF" fill-opacity="0.92" stroke="#0B2545" stroke-width="2.5"/>
  <ellipse cx="138" cy="70" rx="44" ry="17" transform="rotate(32 138 70)"
           fill="#FFFFFF" fill-opacity="0.92" stroke="#0B2545" stroke-width="2.5"/>
  <!-- legs -->
  <g stroke="#0B2545" stroke-width="4" stroke-linecap="round" fill="none">
    <path d="M92 108 L64 126 L52 156"/>
    <path d="M108 108 L136 126 L148 156"/>
    <path d="M94 116 L76 142 L72 168"/>
    <path d="M106 116 L124 142 L128 168"/>
    <path d="M97 100 L70 98 L54 112"/>
    <path d="M103 100 L130 98 L146 112"/>
  </g>
  <!-- abdomen (striped) -->
  <ellipse cx="100" cy="136" rx="14" ry="30" fill="#0B2545"/>
  <g fill="#FFB703">
    <rect x="86.5" y="124" width="27" height="4" rx="2"/>
    <rect x="87.5" y="136" width="25" height="4" rx="2"/>
    <rect x="89" y="148" width="22" height="4" rx="2"/>
  </g>
  <!-- thorax and head -->
  <ellipse cx="100" cy="98" rx="17" ry="20" fill="#0B2545"/>
  <circle cx="100" cy="72" r="12" fill="#0B2545"/>
  <!-- antennae -->
  <path d="M94 62 Q86 50 78 48 M106 62 Q114 50 122 48" stroke="#0B2545"
        stroke-width="3" stroke-linecap="round" fill="none"/>
  <!-- proboscis (points forward from the head) -->
  <path d="M100 60 L100 30" stroke="#0B2545" stroke-width="4" stroke-linecap="round"/>
  <!-- eye -->
  <circle cx="96" cy="70" r="3.2" fill="#FFB703"/>
</svg>
"""
