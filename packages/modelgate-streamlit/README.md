# modelgate-streamlit (archived)

This is the original Streamlit UI built during the UAS phase of this
project. It is **archived, not actively maintained** — new development
happens entirely in `packages/modelgate-core` (the CLI/library), per
the project's pivot to a library-first focus.

`packages/modelgate-web` (the React frontend this was once paired
with) is archived too, and known broken against the current server API
— so is `packages/modelgate-server` itself. This UI talks to that
server over HTTP; reviving it means reviving that whole stack first.
