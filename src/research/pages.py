"""Local encyclopedia used by the eval and the offline browser.

The pages are the web the pipeline is allowed to see. Answers are not stored
next to the questions; the extractor has to read the HTML.
"""

from __future__ import annotations

HTML: dict[str, str] = {
    "northwind": """<!DOCTYPE html>
<html><head><title>Northwind Labs</title></head><body><article>
<h1>Northwind Labs</h1>
<table class="facts">
<tr><th>Founded</th><td>2014</td></tr>
<tr><th>Founder</th><td>Mira Chen</td></tr>
<tr><th>First product</th><td>Harbor Relay</td></tr>
</table>
<p>Northwind Labs was founded in 2014 by Mira Chen.</p>
<p>Its first product was Harbor Relay, shipped in 2016.</p>
<p>A workshop it later bought was founded in 1972.</p>
</article></body></html>""",
    "kepler": """<!DOCTYPE html>
<html><head><title>Kepler Transit</title></head><body><article>
<h1>Kepler Transit</h1>
<table class="facts">
<tr><th>Founded</th><td>2008</td></tr>
<tr><th>Founder</th><td>Adam Okonkwo</td></tr>
<tr><th>First product</th><td>Route Ledger</td></tr>
</table>
<p>Kepler Transit was founded in 2008 by Adam Okonkwo.</p>
<p>Its first product was Route Ledger.</p>
<p>Kepler Transit sells software to Northwind Labs.</p>
</article></body></html>""",
    "lumen": """<!DOCTYPE html>
<html><head><title>Lumen Field Notes</title></head><body><article>
<h1>Lumen Field Notes</h1>
<table class="facts">
<tr><th>Founded</th><td>2019</td></tr>
<tr><th>Founder</th><td>Priya Shah</td></tr>
<tr><th>First product</th><td>Desk Lamp</td></tr>
</table>
<p>Lumen Field Notes was founded in 2019 by Priya Shah.</p>
<p>Its first product was Desk Lamp.</p>
</article></body></html>""",
    "orion": """<!DOCTYPE html>
<html><head><title>Orion Metals</title></head><body><article>
<h1>Orion Metals</h1>
<table class="facts">
<tr><th>Founded</th><td>1998</td></tr>
<tr><th>Founder</th><td>Helen Park</td></tr>
<tr><th>First product</th><td>Cold Roll</td></tr>
</table>
<p>Orion Metals was founded in 1998 by Helen Park.</p>
<p>Its first product was Cold Roll.</p>
</article></body></html>""",
    "harbor-city": """<!DOCTYPE html>
<html><head><title>Harbor City</title></head><body><article>
<h1>Harbor City</h1>
<table class="facts">
<tr><th>Population</th><td>482130</td></tr>
<tr><th>Incorporated</th><td>1889</td></tr>
<tr><th>Mayor</th><td>Elena Voss</td></tr>
</table>
<p>The population of Harbor City is 482130.</p>
<p>Harbor City was incorporated in 1889.</p>
<p>The mayor of Harbor City is Elena Voss.</p>
</article></body></html>""",
    "cedar": """<!DOCTYPE html>
<html><head><title>Cedar County</title></head><body><article>
<h1>Cedar County</h1>
<table class="facts">
<tr><th>Population</th><td>91440</td></tr>
<tr><th>Incorporated</th><td>1854</td></tr>
<tr><th>Mayor</th><td>Jonah Hale</td></tr>
</table>
<p>The population of Cedar County is 91440.</p>
<p>Cedar County was incorporated in 1854.</p>
<p>The mayor of Cedar County is Jonah Hale.</p>
</article></body></html>""",
    "harbor-relay": """<!DOCTYPE html>
<html><head><title>Harbor Relay</title></head><body><article>
<h1>Harbor Relay</h1>
<table class="facts">
<tr><th>Released</th><td>2016</td></tr>
<tr><th>Price</th><td>49</td></tr>
<tr><th>Maker</th><td>Northwind Labs</td></tr>
</table>
<p>Harbor Relay was released in 2016.</p>
<p>The price of Harbor Relay is 49.</p>
<p>Harbor Relay is made by Northwind Labs.</p>
</article></body></html>""",
    "route-ledger": """<!DOCTYPE html>
<html><head><title>Route Ledger</title></head><body><article>
<h1>Route Ledger</h1>
<table class="facts">
<tr><th>Released</th><td>2010</td></tr>
<tr><th>Price</th><td>120</td></tr>
<tr><th>Maker</th><td>Kepler Transit</td></tr>
</table>
<p>Route Ledger was released in 2010.</p>
<p>The price of Route Ledger is 120.</p>
<p>Route Ledger is made by Kepler Transit.</p>
</article></body></html>""",
    "lectures": """<!DOCTYPE html>
<html><head><title>Community Lectures</title></head><body><article>
<h1>Community Lectures</h1>
<p>Northwind Labs sponsors a lecture series downtown.</p>
</article></body></html>""",
    "workshop": """<!DOCTYPE html>
<html><head><title>Old Workshop</title></head><body><article>
<h1>Old Workshop</h1>
<table class="facts">
<tr><th>Founded</th><td>1972</td></tr>
</table>
<p>Old Workshop was founded in 1972.</p>
</article></body></html>""",
}

HELD_OUT: list[dict] = [
    {
        "id": "northwind-year",
        "question": "What year was Northwind Labs founded?",
        "schema": {
            "type": "object",
            "required": ["founding_year"],
            "properties": {
                "founding_year": {
                    "type": "integer",
                    "description": "The year the organization was founded",
                }
            },
        },
        "gold": {"founding_year": 2014},
    },
    {
        "id": "northwind-founder",
        "question": "Who founded Northwind Labs?",
        "schema": {
            "type": "object",
            "required": ["founder"],
            "properties": {
                "founder": {
                    "type": "string",
                    "description": "The person who founded the organization",
                }
            },
        },
        "gold": {"founder": "Mira Chen"},
    },
    {
        "id": "northwind-product",
        "question": "What was the first product of Northwind Labs?",
        "schema": {
            "type": "object",
            "required": ["first_product"],
            "properties": {
                "first_product": {
                    "type": "string",
                    "description": "The first product the organization shipped",
                }
            },
        },
        "gold": {"first_product": "Harbor Relay"},
    },
    {
        "id": "kepler-year",
        "question": "What year was Kepler Transit founded?",
        "schema": {
            "type": "object",
            "required": ["founding_year"],
            "properties": {
                "founding_year": {
                    "type": "integer",
                    "description": "The year the organization was founded",
                }
            },
        },
        "gold": {"founding_year": 2008},
    },
    {
        "id": "kepler-founder",
        "question": "Who founded Kepler Transit?",
        "schema": {
            "type": "object",
            "required": ["founder"],
            "properties": {
                "founder": {
                    "type": "string",
                    "description": "The person who founded the organization",
                }
            },
        },
        "gold": {"founder": "Adam Okonkwo"},
    },
    {
        "id": "harbor-population",
        "question": "What is the population of Harbor City?",
        "schema": {
            "type": "object",
            "required": ["population"],
            "properties": {
                "population": {
                    "type": "integer",
                    "description": "The number of residents",
                }
            },
        },
        "gold": {"population": 482130},
    },
    {
        "id": "cedar-mayor",
        "question": "Who is the mayor of Cedar County?",
        "schema": {
            "type": "object",
            "required": ["mayor"],
            "properties": {
                "mayor": {"type": "string", "description": "The mayor of the place"}
            },
        },
        "gold": {"mayor": "Jonah Hale"},
    },
    {
        "id": "harbor-incorporated",
        "question": "What year was Harbor City incorporated?",
        "schema": {
            "type": "object",
            "required": ["incorporated_year"],
            "properties": {
                "incorporated_year": {
                    "type": "integer",
                    "description": "The year the city was incorporated",
                }
            },
        },
        "gold": {"incorporated_year": 1889},
    },
    {
        "id": "relay-released",
        "question": "What year was Harbor Relay released?",
        "schema": {
            "type": "object",
            "required": ["release_year"],
            "properties": {
                "release_year": {
                    "type": "integer",
                    "description": "The year it was released",
                }
            },
        },
        "gold": {"release_year": 2016},
    },
    {
        "id": "ledger-maker",
        "question": "Who makes Route Ledger?",
        "schema": {
            "type": "object",
            "required": ["maker"],
            "properties": {
                "maker": {
                    "type": "string",
                    "description": "The organization that makes the product",
                }
            },
        },
        "gold": {"maker": "Kepler Transit"},
    },
]
