class MyClass:
    def __init__(self, name, age, profession):
        self.name = name
        self.age = age
        self.profession = profession
        self.country = "USA"  # another member variable with default value

# Create an instance of MyClass
my_instance = MyClass("Alice", 30, "Engineer")

# Convert the instance's attributes and values to a dictionary
attributes_dict = my_instance.__dict__

# Print the dictionary
print(attributes_dict)

print(type(my_instance))