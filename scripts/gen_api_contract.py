"""
Regenerate api_contract.md from the live FastAPI schema.

The contract is a rendering of app.openapi(), not a hand-maintained document.
Regenerate it whenever routes or response models change:

    python scripts/gen_api_contract.py

Sections 1, 2 and 6 are prose and are preserved verbatim from the constants
below; everything else is derived from the spec.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.security.base import SecurityBase  # noqa: E402

from app.main import app  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "api_contract.md"


def optional_auth_operations() -> set[str]:
    """
    Operation ids whose only security schemes are auto_error=False.

    OpenAPI cannot express "a token is read if present but not demanded", so
    an optionally-authenticated route is indistinguishable from a required one
    in the spec -- the difference only exists on the route's dependants.

    Routes are keyed by operation id rather than path: recent FastAPI keeps an
    included router nested, so a route's own `path_format` is router-local and
    carries no prefix. The prefix is accumulated here to rebuild the operation
    id the spec uses.
    """

    def schemes(dependant):
        """Every security scheme a route pulls in, at any nesting depth.

        A scheme is just a dependency whose callable is a SecurityBase, so
        this walks the tree rather than reading a dedicated field -- FastAPI
        has moved that field between releases.
        """
        found = []

        for sub in dependant.dependencies:
            if isinstance(sub.call, SecurityBase):
                found.append(sub.call)
            found.extend(schemes(sub))

        return found

    def api_routes(router, prefix=""):
        for route in getattr(router, "routes", []):
            if isinstance(route, APIRoute):
                yield prefix + route.path_format, route
                continue

            ctx = getattr(route, "include_context", None)
            nested = getattr(route, "original_router", None) or (
                route if hasattr(route, "routes") else None
            )
            if nested is not None:
                yield from api_routes(
                    nested, prefix + (getattr(ctx, "prefix", "") or "")
                )

    found: set[str] = set()
    spec_paths = app.openapi()["paths"]

    for path, route in api_routes(app):
        reqs = schemes(route.dependant)
        if not reqs or not all(getattr(r, "auto_error", True) is False for r in reqs):
            continue

        for method in route.methods:
            op = spec_paths.get(path, {}).get(method.lower())
            if op and op.get("operationId"):
                found.add(op["operationId"])

    return found


OPTIONAL_AUTH = optional_auth_operations()


def ref_name(schema: dict) -> str | None:
    ref = schema.get("$ref")
    return ref.rsplit("/", 1)[-1] if ref else None


def type_of(schema: dict) -> str:
    """Render a schema as the short type string the contract uses."""
    if not schema:
        return "object"

    name = ref_name(schema)
    if name:
        return f"`{name}`"

    if "anyOf" in schema:
        return "/".join(type_of(s) for s in schema["anyOf"])

    if "allOf" in schema and len(schema["allOf"]) == 1:
        return type_of(schema["allOf"][0])

    t = schema.get("type")

    if t == "array":
        return f"array of {type_of(schema.get('items', {}))}"
    if t == "null":
        return "null"
    if t == "string":
        fmt = schema.get("format")
        return f"string ({fmt})" if fmt else "string"
    if t:
        return t

    if "enum" in schema:
        return "string"

    return "object"


def default_of(schema: dict) -> str:
    if "default" not in schema:
        return "—"
    d = schema["default"]
    if d == "":
        return "\\`\\`"
    return f"`{json.dumps(d) if not isinstance(d, str) else d}`"


def render_endpoint(path: str, method: str, op: dict, lines: list[str]) -> None:
    lines.append(f"### `{method.upper()} {path}`")
    lines.append("")

    if op.get("summary"):
        lines.append(f"**{op['summary']}**")
        lines.append("")

    if op.get("description"):
        for para in op["description"].strip().split("\n\n"):
            lines.append(" ".join(l.strip() for l in para.strip().splitlines()))
            lines.append("")

    if not op.get("security"):
        auth = "Not required"
    elif op.get("operationId") in OPTIONAL_AUTH:
        auth = "Optional (a bearer token enriches the response; omitting it still succeeds)"
    else:
        auth = "Required"

    lines.append(f"- **Operation ID:** `{op.get('operationId', '')}`")
    lines.append(f"- **Authentication:** {auth}")
    lines.append("")

    params = op.get("parameters", [])
    if params:
        lines.append("#### Parameters")
        lines.append("")
        lines.append("| Name | In | Type | Required | Default |")
        lines.append("| --- | --- | --- | --- | --- |")
        for p in params:
            sch = p.get("schema", {})
            lines.append(
                f"| `{p['name']}` | `{p['in']}` | {type_of(sch)} | "
                f"{'Yes' if p.get('required') else 'No'} | {default_of(sch)} |"
            )
        lines.append("")

    body = op.get("requestBody")
    if body:
        lines.append("#### Request Body")
        lines.append("")
        for ctype, media in body.get("content", {}).items():
            schema = media.get("schema", {})
            name = ref_name(schema) or type_of(schema).strip("`")
            lines.append(f"**Content-Type:** `{ctype}`\\")
            lines.append(f"**Schema:** {'`' + name + '`' if name != 'object' else 'object'}")
        lines.append("")

    lines.append("#### Responses")
    lines.append("")
    lines.append("| Status | Description | Response Schema |")
    lines.append("| --- | --- | --- |")
    for status, resp in op.get("responses", {}).items():
        content = resp.get("content", {})
        schema = next(iter(content.values()), {}).get("schema", {}) if content else {}
        rendered = type_of(schema) if schema else "—"
        lines.append(f"| `{status}` | {resp.get('description', '')} | {rendered} |")
    lines.append("")


def render_schema(name: str, schema: dict, lines: list[str]) -> None:
    lines.append(f"### `{name}`")
    lines.append("")

    if "enum" in schema:
        lines.append("**Enum values:**")
        lines.append("")
        for v in schema["enum"]:
            lines.append(f"- `{v}`")
        lines.append("")
        return

    props = schema.get("properties")
    if not props:
        lines.append("Object with no declared properties in the specification.")
        lines.append("")
        return

    required = set(schema.get("required", []))
    lines.append("| Field | Type | Required | Default / Constraints |")
    lines.append("| --- | --- | --- | --- |")
    for field, sub in props.items():
        lines.append(
            f"| `{field}` | {type_of(sub)} | {'Yes' if field in required else 'No'} | "
            f"{default_of(sub)} |"
        )
    lines.append("")


HEADER = """# Feed Builder API Contract

**OpenAPI:** `{openapi}`\\
**API:** {title}\\
**Version:** {version}

> This document is generated from the live FastAPI schema by
> `scripts/gen_api_contract.py`. Do not edit it by hand -- regenerate it after
> changing routes or response models.

## 1. Authentication

The API uses OAuth2 Password Bearer authentication.

- **Token endpoint:** `POST /auth/login`
- **Token flow:** OAuth2 password flow
- **Header for protected endpoints:** `Authorization: Bearer <access_token>`

### Login request

**Content-Type:** `application/x-www-form-urlencoded`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `username` | string | Yes | Login username |
| `password` | string | Yes | Password |
| `grant_type` | string/null | No | If supplied, must be `password` |
| `scope` | string | No | Defaults to empty string |
| `client_id` | string/null | No | OAuth client id |
| `client_secret` | string/null | No | OAuth client secret |

**Response:** `Token`

```json
{{
  "access_token": "string",
  "token_type": "string"
}}
```

## 2. General Conventions

- IDs are UUID strings unless otherwise stated.
- Cursor-based endpoints accept an optional `cursor` query parameter.
- Paginated endpoints accept an optional `limit` query parameter.
- Validation failures are represented by HTTP `422` with `HTTPValidationError` where defined.
- Protected endpoints require OAuth2 Bearer authentication.
- Each endpoint states whether authentication is **Required**, **Optional**
  or **Not required**. *Optional* means a bearer token is read if supplied and
  enriches the response (for example `is_liked` on posts), but the request
  succeeds without one.
- Union types are written with `/`, so `string (uuid)/null` means a nullable
  UUID.

## 3. Endpoint Contract

"""

NOTES = """## 6. Contract Notes

- This document is generated from the live FastAPI schema; anything not
  expressible in OpenAPI is intentionally absent.
- `PostType` appears twice under different generated names; both contain the
  same six logical post types, with ordering differences.
- Search is backed by OpenSearch. Only publicly visible posts (`is_active`)
  are indexed, and `GET /search` forces that filter regardless of parameters,
  so hidden, held or archived posts never appear in results. An author's own
  hidden posts are served by `GET /posts/my_inactive_posts` instead.
- Search returns entity ids that are hydrated from the cache, so post and user
  objects in a search response carry the same fields they do everywhere else.
"""


def main() -> int:
    spec = app.openapi()
    lines: list[str] = []

    lines.append(
        HEADER.format(
            openapi=spec.get("openapi", "3.1.0"),
            title=spec["info"]["title"],
            version=spec["info"]["version"],
        ).rstrip("\n")
    )
    lines.append("")

    methods = ("get", "post", "put", "patch", "delete")
    for path, ops in spec["paths"].items():
        for method in methods:
            if method in ops:
                render_endpoint(path, method, ops[method], lines)

    lines.append("## 4. Schemas")
    lines.append("")
    for name, schema in sorted(spec.get("components", {}).get("schemas", {}).items()):
        render_schema(name, schema, lines)

    lines.append("## 5. Security Scheme")
    lines.append("")
    lines.append("### `OAuth2PasswordBearer`")
    lines.append("")
    lines.append("- **Type:** OAuth2")
    lines.append("- **Flow:** Password")
    lines.append("- **Token URL:** `/auth/login`")
    lines.append("- **Scopes:** None defined")
    lines.append("")
    lines.append(NOTES.rstrip("\n"))
    lines.append("")

    OUT.write_text("\n".join(lines))
    n_ep = sum(1 for ops in spec["paths"].values() for m in methods if m in ops)
    n_sc = len(spec.get("components", {}).get("schemas", {}))
    print(f"wrote {OUT.name}: {n_ep} endpoints, {n_sc} schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
