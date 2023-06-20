from typing import Optional, Any


class Executor:

    """
    use this method to drive the user interface to fill the necessary parameters & preconditions
    to execute what was created. Optionally return a result to send as feedback
    """
    def run(self) -> Optional[Any]:
        raise NotImplementedError("you must implement this method.")


    """
    use this method to make changes to the recipe after it has been modified and 
    executed by the user
    
    should return a recipe
    """
    def update(self) -> dict:
        raise NotImplementedError("you must implement this method.")
