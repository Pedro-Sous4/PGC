import tkinter as tk
from tkinter import messagebox, ttk
import json
import os

class TodoListManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Todo List Manager")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        self.todos = []
        self.load_todos()
        
        self.setup_ui()
        self.update_todo_list()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Todo List", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Todo input
        self.todo_entry = ttk.Entry(input_frame, width=40)
        self.todo_entry.grid(row=0, column=0, padx=(0, 10))
        self.todo_entry.bind('<Return>', lambda e: self.add_todo())
        
        # Add button
        add_button = ttk.Button(input_frame, text="Add Todo", command=self.add_todo)
        add_button.grid(row=0, column=1)
        
        # Todo list frame
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Todo listbox
        self.todo_listbox = tk.Listbox(list_frame, width=50, height=20, 
                                      yscrollcommand=scrollbar.set, 
                                      selectmode=tk.SINGLE)
        self.todo_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.todo_listbox.yview)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(20, 0))
        
        # Action buttons
        complete_button = ttk.Button(button_frame, text="Complete/Uncomplete", command=self.toggle_complete)
        complete_button.grid(row=0, column=0, padx=(0, 10))
        
        delete_button = ttk.Button(button_frame, text="Delete", command=self.delete_todo)
        delete_button.grid(row=0, column=1, padx=(0, 10))
        
        clear_completed_button = ttk.Button(button_frame, text="Clear Completed", command=self.clear_completed)
        clear_completed_button.grid(row=0, column=2)
    
    def add_todo(self):
        todo_text = self.todo_entry.get().strip()
        if todo_text:
            todo = {
                'text': todo_text,
                'completed': False
            }
            self.todos.append(todo)
            self.todo_entry.delete(0, tk.END)
            self.update_todo_list()
            self.save_todos()
        else:
            messagebox.showwarning("Input Error", "Please enter a todo item.")
    
    def delete_todo(self):
        selected_index = self.todo_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            del self.todos[index]
            self.update_todo_list()
            self.save_todos()
        else:
            messagebox.showwarning("Selection Error", "Please select a todo item to delete.")
    
    def toggle_complete(self):
        selected_index = self.todo_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            self.todos[index]['completed'] = not self.todos[index]['completed']
            self.update_todo_list()
            self.save_todos()
        else:
            messagebox.showwarning("Selection Error", "Please select a todo item to toggle completion.")
    
    def clear_completed(self):
        self.todos = [todo for todo in self.todos if not todo['completed']]
        self.update_todo_list()
        self.save_todos()
    
    def update_todo_list(self):
        self.todo_listbox.delete(0, tk.END)
        for todo in self.todos:
            display_text = todo['text']
            if todo['completed']:
                display_text = f"✓ {display_text}"
            self.todo_listbox.insert(tk.END, display_text)
            
            # Color code completed items
            if todo['completed']:
                self.todo_listbox.itemconfig(tk.END, fg='green')
    
    def save_todos(self):
        try:
            with open('todos.json', 'w') as f:
                json.dump(self.todos, f, indent=2)
        except Exception as e:
            print(f"Error saving todos: {e}")
    
    def load_todos(self):
        if os.path.exists('todos.json'):
            try:
                with open('todos.json', 'r') as f:
                    self.todos = json.load(f)
            except Exception as e:
                print(f"Error loading todos: {e}")
                self.todos = []

def main():
    root = tk.Tk()
    app = TodoListManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()