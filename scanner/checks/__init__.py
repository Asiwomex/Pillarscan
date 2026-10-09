"""One check per module, named after its check_id.

Each module defines:

    META: CheckMeta
    def run(ctx: CheckContext) -> Iterable[Finding]

run() reports one finding per resource it evaluates, pass or fail. It may
raise: the engine turns any exception into a finding with status "error".
Checks only ever call read APIs (Get*, List*, Describe*).
"""
