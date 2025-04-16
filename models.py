class Task:
    def __init__(self, text, priority="medium", due_date=None, completed=False, position=0):
        self.text = text
        self.priority = priority
        self.due_date = due_date
        self.completed = completed
        self.position = position

    def to_dict(self):
        return {
            'text': self.text,
            'priority': self.priority,
            'dueDate': self.due_date,
            'completed': self.completed,
            'position': self.position
        }

    @staticmethod
    def from_dict(data):
        return Task(
            text=data['text'],
            priority=data.get('priority', 'medium'),
            due_date=data.get('dueDate'),
            completed=data.get('completed', False),
            position=data.get('position', 0)
        )
