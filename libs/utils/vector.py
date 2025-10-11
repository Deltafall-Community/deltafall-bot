import math

class Vector2D:
    def __init__(self, x, y):
        """Initializes a 2D vector with x and y components."""
        self.x = x
        self.y = y

    def __repr__(self):
        """Provides a string representation for the vector."""
        return f"Vector2D({self.x}, {self.y})"

    def __add__(self, other):
        """Adds two vectors or a vector and a scalar."""
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        elif isinstance(other, (int, float)):
            return Vector2D(self.x + other, self.y + other)
        elif isinstance(other, tuple) and (len(other) == 2) and (isinstance(other[0], (int, float)) and isinstance(other[0], (int, float))):
            return Vector2D(self.x + other[0], self.y + other[1])
        else:
            raise TypeError("Unsupported operand type for +")

    def __sub__(self, other):
        """Subtracts two vectors or a scalar from a vector."""
        if isinstance(other, Vector2D):
            return Vector2D(self.x - other.x, self.y - other.y)
        elif isinstance(other, (int, float)):
            return Vector2D(self.x - other, self.y - other)
        else:
            raise TypeError("Unsupported operand type for -")

    def __mul__(self, scalar):
        """Multiplies the vector by a scalar."""
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x * scalar, self.y * scalar)
        else:
            raise TypeError("Unsupported operand type for *")

    def dot(self, other):
        """Calculates the dot product with another vector."""
        if isinstance(other, Vector2D):
            return self.x * other.x + self.y * other.y
        else:
            raise TypeError("Dot product can only be calculated with another Vector2D")

    def magnitude(self):
        """Calculates the magnitude (length) of the vector."""
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self):
        """Returns a new normalized vector (unit vector)."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)  # Handle zero vector case
        return Vector2D(self.x / mag, self.y / mag)

    def to_tuple(self):
        """
        Returns the vector components as a tuple (x, y).
        This is useful for functions that expect a tuple of coordinates,
        such as those in the Pillow (PIL) library.
        """
        return (int(self.x), int(self.y)) # Often Pillow expects integer coordinates
    
    @classmethod
    def from_tuple(cls, coords_tuple):
        """
        Creates a new Vector2D from a tuple of (x, y) coordinates.

        Args:
            coords_tuple (tuple): A tuple containing two numeric values (x, y).

        Returns:
            Vector2D: A new Vector2D instance.

        Raises:
            TypeError: If coords_tuple is not a tuple or does not contain numbers.
            ValueError: If coords_tuple does not have exactly two elements.
        """
        if not isinstance(coords_tuple, tuple):
            raise TypeError("Input to from_tuple must be a tuple.")
        if len(coords_tuple) != 2:
            raise ValueError("Tuple must contain exactly two elements (x, y).")
        x, y = coords_tuple
        return cls(x, y) # cls(x, y) calls the __init__ method of the class
