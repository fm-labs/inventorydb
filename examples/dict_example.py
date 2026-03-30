# Simple To-do List Example
from inventorydb.inventory import Inventory
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage

todos_inventory = Inventory(item_type="todo", storage=InMemoryInventoryStorage())  # Replace with actual storage instance

# Create a new to-do item
new_todo = {"id": "1", "name": "Buy groceries", "status": "pending"}
created_todo = todos_inventory.save(new_todo)
print("Created To-do:", created_todo)

# Read the to-do item
fetched_todo = todos_inventory.get("1")
print("Fetched To-do:", fetched_todo)

# Update the to-do item
updated_todo = todos_inventory.patch("1", {"status": "completed"})
print("Updated To-do:", updated_todo)

# Delete the to-do item (not implemented yet)
# delete_result = todos.delete("1")
# print("Deleted To-do:", delete_result)

