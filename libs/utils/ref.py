from typing import Any, Sequence

class Ref:
    def __init__(self, root: Any, indices: Sequence[int] = ()):
        self.root = root
        self.indices = list(indices)

    # --- core helpers ---
    def get(self):
        value = self.root
        for idx in self.indices:
            value = value[idx]
        return value

    def _set_in_container(self, container, key, value):
        """Handles replacement in both lists and tuples safely."""
        # Ensure we're working with a real container
        if isinstance(container, Ref):
            container = container.get()

        if isinstance(container, list):
            container[key] = value
            return container

        elif isinstance(container, tuple):
            # tuples are immutable, create a new one
            return container[:key] + (value,) + container[key + 1:]

        else:
            raise TypeError(f"Unsupported container type: {type(container)}")

    def set(self, value):
        """Recursively updates value and propagates through tuples."""
        if not self.indices:
            # Replace root entirely
            self.root = value
            return self.root

        # Get parent reference and actual parent container
        parent_ref = Ref(self.root, self.indices[:-1])
        parent = parent_ref.get()
        key = self.indices[-1]

        new_parent = self._set_in_container(parent, key, value)

        # Recursively propagate upward if parent was tuple
        if isinstance(parent, tuple):
            return parent_ref.set(new_parent)
        else:
            self._set_in_container(parent, key, value)
            return self.root

    # --- utility ---
    def append(self, value):
        """Appends to lists or tuples by converting if needed."""
        target = self.get()

        if isinstance(target, list):
            target.append(value)
            return self.root

        elif isinstance(target, tuple):
            # Convert to list, append, then back to tuple
            temp = list(target)
            temp.append(value)
            new_tuple = tuple(temp)
            return self.set(new_tuple)

        else:
            raise TypeError(f"Cannot append to type {type(target)}")

    def __repr__(self):
        try:
            val = self.get()
        except Exception:
            val = "<invalid>"
        return f"<Ref {self.indices} -> {val!r}>"


    def __len__(self):
        """Return len() of the underlying value."""
        return len(self.get())

    def __getitem__(self, key):
        """Allow indexing like ref[2] instead of Ref(root, [2])."""
        return Ref(self.root, self.indices + [key])

    def __iter__(self):
        """Allow iteration: for x in ref."""
        return iter(self.get())

    def __contains__(self, item):
        """Allow 'in' checks."""
        return item in self.get()