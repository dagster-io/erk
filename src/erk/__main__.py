"""Allow erk to be run as a module: python -m erk."""

print("hello")

from erk import main  # noqa: E402

if __name__ == "__main__":
    main()
