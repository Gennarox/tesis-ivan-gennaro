import os

# Print Hello World
print("Hello, world!")

# Create outputs folder if it doesn't exist
os.makedirs("outputs", exist_ok=True)

# Save empty text file
with open("outputs/empty.txt", "w") as f:
    pass  # creates an empty file
