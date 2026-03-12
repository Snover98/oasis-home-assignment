# Project: Oasis Home Assignment - NHI Ticket System


This project contains a python backend and a react frontend.

## Development

See `README.md` for project specifications and requirements

### Python Standards
*   **Style:** Follow the PEP 8 style guide.
*   **Docstrings:** Add or update docstrings for any new or modified functions.
*   **Testing:** This project currently lacks automated tests. When adding new features, please also add a corresponding test file.
*   **Type Hints:** use type hints for method signatures (params & retval), as well as class fields - always use python builtins over the typing module. typing.Union should not be used, use `|` instead
*   **main function:** whenever running code under `if __name__ == '__main__':` do not define any variables - any code running there should be defined in a function called `main` which will be called from the `if` statement.
*   Use the uv package manager for python code

### Typescript Standards

This project follows strict TypeScript standards to ensure maintainability and type safety.

#### 1. Naming Conventions
- **Files**: Use `kebab-case` for file names (e.g., `jira-service.ts`, `auth-middleware.ts`).
- **Types & Interfaces**: Use `PascalCase`. Do **not** prefix interfaces with `I`.
- **Functions & Variables**: Use `camelCase`.
- **Constants**: Use `UPPER_SNAKE_CASE` for global constants.
- **Enums**: Use `PascalCase` for both the enum name and its values.

#### 2. Type Safety
- **Strict Mode**: `strict: true` is enabled in `tsconfig.json`.
- **Avoid `any`**: Use `unknown` if the type is truly unknown, and use type guards to narrow it down.
- **Explicit Returns**: Always define the return type of exported functions to improve readability and catch errors early.
- **Interfaces vs. Types**: 
  - Use `interface` for public API definitions (to allow declaration merging).
  - Use `type` for unions, intersections, and complex utility types.

#### 3. Best Practices
- **Immutability**: Prefer `const` over `let`. Avoid `var` entirely.
- **Null Safety**: Use `undefined` instead of `null` unless required by an external library (like Jira API).
- **Optional Chaining**: Use `?.` and `??` (nullish coalescing) instead of complex ternary or `&&` checks.
- **Async/Await**: Always use `async/await` instead of raw `.then()` chains for better error handling with `try/catch`.

#### 4. Project Structure
```text
src/
 ├── api/           # REST Controllers & Routes
 ├── services/      # Business logic (Jira integration, Blog fetcher)
 ├── models/        # TypeScript interfaces & Enums
 ├── middleware/    # Auth & Validation
 └── utils/         # Helpers & AI logic

## Tool Usage Guidelines

When utilizing documentation and code example retrieval:

*   **Context7 Library ID Resolution:** Always use the `resolve_library_id` tool before `query_docs` to obtain a valid Context7-compatible library ID.
*   **Explicit Library IDs:** If you are explicitly provided with a library ID in the format `/org/project` or `/org/project/version`, you may directly use `query_docs` with that ID, skipping `resolve_library_id`.
*   **Query Specificity:** Ensure your queries for `query_docs` are specific and detailed to retrieve the most relevant information.

