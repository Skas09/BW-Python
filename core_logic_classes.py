import pandas as pd
from datetime import datetime, timedelta
import csv
import os
import io
import codecs


class Transaction:
    """
    Represents a financial transaction with attributes for date, department, value, and beneficiary.

    Provides utilities for equality comparison, hashability, CSV reading, 
    and fuzzy matching based on date tolerance.
    """
    def __init__(self, date: str, department: str, value: str, beneficiary: str):
        """
        Initializes a Transaction object.

        Args:
            date (str): The date of the transaction in 'YYYY-MM-DD' format.
            department (str): The department responsible for the transaction.
            value (str): The monetary value of the transaction.
            beneficiary (str): The entity receiving the transaction.
        """
        self.date = date
        self.department = department
        self.value = value
        self.beneficiary = beneficiary

    def to_list(self):
        """
        Converts the transaction into a list.

        Returns:
            list: A list representation [date, department, value, beneficiary].
        """
        return [self.date, self.department, self.value, self.beneficiary]

    def __eq__(self, other):
        """
        Checks equality between two Transaction objects.

        Args:
            other (Transaction): Another transaction to compare with.

        Returns:
            bool: True if all attributes match, False otherwise.
        """
        if not isinstance(other, Transaction):
            return False
        return (
            self.date == other.date and
            self.department == other.department and
            self.value == other.value and
            self.beneficiary == other.beneficiary
        )

    def __hash__(self):
        """
        Returns a hash of the transaction for use in sets and dictionaries.

        Returns:
            int: The hash value.
        """
        return hash((self.date, self.department, self.value, self.beneficiary))

    @classmethod
    def from_list(cls, row):
        """
        Instantiates a Transaction from a list of string elements.

        Args:
            row (list): A list in the format [date, department, value, beneficiary].

        Returns:
            Transaction: A new Transaction object.
        """
        return cls(*row)
    
    @staticmethod
    def read_transaction_csv(path: str) -> pd.DataFrame:
        """
        Reads a CSV file of transactions and returns it as a pandas DataFrame.

        The CSV must contain rows with four columns: date, department, value, and beneficiary.
        Missing headers will be replaced with default column names.

        Args:
            path (str): Path to the CSV file.

        Returns:
            pd.DataFrame or None: DataFrame of transaction data, or None if empty or error.
        """
        df = pd.read_csv(path, header=None, dtype=str)
        try:
            if df.empty:
                print(f"The file '{path}' is empty.")
                return None

            df.columns = ["Data", "Departamento", "Valor", "Beneficiário"]
            return df

        except FileNotFoundError:
            print(f"The file '{path}' was not found.")
            return None

        except Exception as e:
            print(f"An error occurred while reading '{path}': {str(e)}")
            return None
        
    def is_match_with_tolerance(self, other: 'Transaction') -> bool:
        """
        Checks whether two transactions match, allowing a ±1 day difference in the date.

        Args:
            other (Transaction): The other transaction to compare against.

        Returns:
            bool: True if all other fields match and dates are within one day, False otherwise.
        """
        if (
            self.department != other.department or
            self.value != other.value or
            self.beneficiary != other.beneficiary
        ):
            return False

        try:
            date1 = datetime.strptime(self.date, "%Y-%m-%d")
            date2 = datetime.strptime(other.date, "%Y-%m-%d")
        except ValueError:
            return False  # invalid date format

        delta = abs((date1 - date2).days)
        return delta <= 1


class TransactionReconciler:
    """
    Reconciles two groups of financial transactions by matching them with tolerance.

    Each transaction from one group is compared to the other group, allowing a ±1 day
    date difference and requiring all other fields to match. Results are labeled as
    'FOUND' or 'MISSING' depending on whether a corresponding transaction exists.
    """
    def __init__(self, group_a: list, group_b: list):
        """
        Initializes the reconciler with two groups of Transaction objects.

        Args:
            group_a (list): List of Transaction objects from the first group.
            group_b (list): List of Transaction objects from the second group.
        """
        self.group_a = group_a
        self.group_b = group_b

    def reconcile(self):
        """
        Performs the reconciliation between group_a and group_b.

        A transaction is considered a match if the department, value, and beneficiary
        match, and the date is the same or differs by no more than one day.
        Each transaction can match only once. Preference is given to the earliest date
        when multiple matches exist.

        Returns:
            tuple: Two lists of lists. Each inner list represents a transaction with an
                   added column: 'FOUND' if matched or 'MISSING' otherwise.
                   Format: (result_from_a, result_from_b)
        """
        matched_b_indices = set()
        result_a = []

        for idx_a, tx_a in enumerate(self.group_a):
            candidates = [
                (idx_b, tx_b)
                for idx_b, tx_b in enumerate(self.group_b)
                if idx_b not in matched_b_indices and tx_a.is_match_with_tolerance(tx_b)
            ]

            if candidates:
                # Sort candidates by date (ascending) to match the earliest
                candidates.sort(key=lambda x: x[1].date)
                idx_b_match, _ = candidates[0]
                matched_b_indices.add(idx_b_match)
                result_a.append(tx_a.to_list() + ["FOUND"])
            else:
                result_a.append(tx_a.to_list() + ["MISSING"])

        # Repeat logic for B, checking matches in A
        matched_a_indices = set()
        result_b = []

        for idx_b, tx_b in enumerate(self.group_b):
            candidates = [
                (idx_a, tx_a)
                for idx_a, tx_a in enumerate(self.group_a)
                if idx_a not in matched_a_indices and tx_b.is_match_with_tolerance(tx_a)
            ]

            if candidates:
                candidates.sort(key=lambda x: x[1].date)
                idx_a_match, _ = candidates[0]
                matched_a_indices.add(idx_a_match)
                result_b.append(tx_b.to_list() + ["FOUND"])
            else:
                result_b.append(tx_b.to_list() + ["MISSING"])

        return result_a, result_b

    @staticmethod
    def save_reconcile_csv(out1: list[list[str]], path1: str, out2: list[list[str]], path2: str):
        """
        Saves the reconciliation results to two separate CSV files.

        Args:
            out1 (list[list[str]]): Reconciled results for group A.
            path1 (str): File path to save group A's results.
            out2 (list[list[str]]): Reconciled results for group B.
            path2 (str): File path to save group B's results.
        """
        try:
            with open(path1, mode='w', newline='', encoding='utf-8') as f1:
                writer = csv.writer(f1)
                writer.writerows(out1)

            with open(path2, mode='w', newline='', encoding='utf-8') as f2:
                writer = csv.writer(f2)
                writer.writerows(out2)

            print(f"✅ Files saved: {path1}, {path2}")
        except Exception as e:
            print(f"Error saving CSV files: {str(e)}")

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Class to handle with problem two: last_lines
class txt_lines:
    """
    A utility class for reading and processing text files line by line, 
    with support for forward iteration, resetting, and memory-efficient 
    reverse reading using buffered UTF-8 decoding.

    Features:
    ---------
    - Load lines from a UTF-8 encoded text file
    - Iterate through lines using next()
    - Reset the iterator to the beginning
    - Reverse lines efficiently using chunked binary reads (UTF-8 safe)
    
    Notes:
    ------
    - The reverse_lines_chunked method reads the file from the end,
      in fixed-size chunks (default 8192 bytes) without breaking multi-byte characters.
    - It supports all UTF-8 characters and handles both Unix (`\\n`) and Windows (`\\r\\n`) line endings.
    - Output lines are normalized to end with `\\n`.

    Parameters:
    -----------
    filepath : str
        Path to the UTF-8 encoded text file to be processed.
    """
    def __init__(self, filepath: str = None):
        """
        Initializes the txt_lines object and optionally loads lines from a file.

        Args:
            filepath (str, optional): Path to the text file to read. If not provided,
                                      the object will be initialized with an empty line list.
        """
        self.lines_iterator = 0
        self.filepath = filepath
        self.lines = self.read_lines() if filepath else []

    def read_lines(self):
        """
        Reads the file at self.filepath and returns its lines.

        Returns:
            list: List of lines read from the file.
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines

    def __next__(self):
        """
        Returns the next line in the file, incrementing the internal iterator.

        Returns:
            str: The current line.

        Raises:
            StopIteration: If the end of the line list is reached.
        """
        if self.lines_iterator >= len(self.lines):
            return print("No more lines to iterate.\n" 
                    "If you like to reset the iterator, use the object.reset() method.")
        current_line = self.lines[self.lines_iterator]
        self.lines_iterator += 1
        return current_line

    def reset(self):
        """
        Resets the internal line iterator to the beginning of the file.
        """
        self.lines_iterator = 0

    def reverse_lines_chunked(self, chunk_size: int = io.DEFAULT_BUFFER_SIZE):
        """
        Reads the file in reverse order, line by line, using fixed-size chunks of bytes.

        This method avoids loading the entire file into memory, making it efficient for
        large files. It processes the file from end to start, reading binary chunks 
        and decoding them safely using UTF-8, ensuring multibyte characters are not split.

        buffer: temporary area in memory used to hold data while it’s being transferred.
        UTF-8: way to represent text using bytes.
        chunk: a piece of data that is read or written in one go.

        Parameters:
        -----------
        chunk_size : int, optional
            Maximum number of bytes to read at a time. Defaults to io.DEFAULT_BUFFER_SIZE (usually 8192 bytes).

        Behavior:
        ---------
        - Opens the file in binary mode ('rb')
        - Reads backward from the end of the file in chunks of up to `chunk_size` bytes
        - Buffers raw data until a full line (ending in `\n`) is detected
        - Handles both Windows (`\r\n`) and Unix (`\n`) line endings
        - Uses an incremental UTF-8 decoder to avoid breaking multibyte characters
        - Final output lines are stored in self.lines in reversed order, all ending in `\n`

        Returns:
        --------
        list[str]
            A list of decoded lines in reverse order, each line ending with '\n'.

        Raises:
        -------
        Prints error messages if the file is not found or decoding fails unexpectedly.
        """

        # io.DEFAULT_BUFFER_SIZE 8192 bytes -> Control the size of the chunks read from the file
        self.lines = []
        buffer = b"" # Variable to hold the bytes read from the file
        newline = b"\n" # Variable to detect the end of a line

        try:
            with open(self.filepath, 'rb') as f:
                f.seek(0, os.SEEK_END) # Move the cursor to the end of the file
                position = f.tell() # Get the total file size in bytes. -> Used to show the position of the cursor in the file

                while position > 0:
                    read_size = min(chunk_size, position) # Calculate how much to read (never go below position 0).
                    position -= read_size # Move backward and read a chunk of bytes from the file. ->  "window" of the file to analyze.
                    f.seek(position)
                    chunk = f.read(read_size)
                    buffer = chunk + buffer # Prepend the newly read chunk to the front of the buffer.

                    # Extract full lines from buffer
                    while True:
                        nl_index = buffer.rfind(newline) # Search for the last newline (\n) in the buffer.
                        if nl_index == -1:
                            break # If none is found, break out and wait for more data from the next chunk.

                        line_bytes = buffer[nl_index + 1:] # line_bytes gets everything after the last newline (i.e., a full line).
                        buffer = buffer[:nl_index + 1] # Trim that line from the buffer.

                        try:
                            line = line_bytes.decode("utf-8") # Try to decode the extracted line safely.
                            if len(line) > 0: # Check if the line is not empty.:
                                self.lines.append(line.rstrip('\r') + '\n') # If it works, append it to the reversed lines list.
                            buffer = buffer[:nl_index] # Trim the buffer to remove the processed line.
                        except UnicodeDecodeError:
                            buffer = line_bytes + buffer # caught a UTF-8 character split across chunks, undo the split by putting it back into the buffer and breaking (wait for next chunk).
                            break

                # Handle any remaining bytes
                if buffer:
                    try:
                        line = buffer.decode("utf-8")
                        self.lines.append(line.rstrip('\r') + '\n')
                    except UnicodeDecodeError:
                        print(" Warning: Could not decode some final bytes.")

            # Return lines collected in reverse order
            return self.lines

        except FileNotFoundError:
            print(f"File not found: {self.filepath}")
            return []
        except Exception as e:
            print(f"Error during chunked reverse read: {e}")
            return []
        


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Class and functions to handle with problem three: computed_property

# Unique object used as a placeholder for missing attributes
_MISSING = object()


def computed_property(*dependencies):
    """
    Decorator that creates a computed property with caching based on attribute dependencies.

    The result is cached and reused as long as the specified dependent attributes remain unchanged.
    If any dependency changes, the value is recalculated.

    Args:
        *dependencies (str): One or more attribute names that the property depends on.

    Returns:
        function: A wrapper that turns a method into a ComputedProperty.
    """
    def wrapper(func):
        return ComputedProperty(func, dependencies)
    return wrapper

def _inject_setattr(cls):
    """
    Dynamically injects a custom __setattr__ into a class to track attribute changes.

    When a dependent attribute is updated, any computed properties relying on it are invalidated
    by clearing the relevant entries from the internal cache.

    Args:
        cls (type): The class to modify.
    """
    if hasattr(cls, "_has_custom_setattr"):
        return 

    original_setattr = cls.__setattr__

    def custom_setattr(self, name, value):
        # Invalidate cache if a dependency is updated
        if '_computed_cache' in self.__dict__:
            for key, (_, deps) in list(self.__dict__['_computed_cache'].items()):
                if name in deps:
                    del self.__dict__['_computed_cache'][key]
        original_setattr(self, name, value)

    cls.__setattr__ = custom_setattr
    cls._has_custom_setattr = True

class ComputedProperty:
    """
    Descriptor that represents a cached computed property.

    The value is cached based on a set of dependent attributes. If any of those attributes change,
    the cache is invalidated and the property is recomputed on the next access.

    Supports custom setter and deleter methods, similar to the built-in @property decorator.
    """
    def __init__(self, func, dependencies):
        """
        Initializes the computed property.

        Args:
            func (function): The function defining the computed value.
            dependencies (Iterable[str]): Attribute names that the property depends on.
        """
        self.func = func
        self.dependencies = set(dependencies)
        self._name = func.__name__
        self._setter = None
        self._deleter = None
        self.__doc__ = func.__doc__

    def __get__(self, instance, owner):
        """
        Gets the property value, using cache if dependencies haven't changed.

        Args:
            instance (object): The object instance that owns this property.
            owner (type): The class to which the instance belongs.

        Returns:
            Any: The computed or cached value of the property.
        """
        if instance is None:
            return self

        _inject_setattr(type(instance))  # ensures setattr override 

        # Get or initialize the cache
        cache = instance.__dict__.setdefault('_computed_cache', {})

        # Compute the current values of dependencies (ignoring missing attributes)
        current_deps = tuple(
            getattr(instance, dep, _MISSING) for dep in self.dependencies
        )

        # If the property has already cached a value and dependencies haven't changed, return it
        if self._name in cache:
            cached_value, last_deps = cache[self._name]
            if current_deps == last_deps:
                return cached_value

        # Otherwise, compute and cache the new value
        result = self.func(instance)
        cache[self._name] = (result, current_deps)
        return result

    def __set__(self, instance, value):
        """
        Sets the property value using a custom setter if defined.

        Args:
            instance (object): The instance on which to set the property.
            value (Any): The value to assign.

        Raises:
            AttributeError: If no setter is defined.
        """
        if self._setter is None:
            raise AttributeError(f"Can't set attribute '{self._name}'")
        return self._setter(instance, value)

    def __delete__(self, instance):
        """
        Deletes the property value using a custom deleter if defined.

        Args:
            instance (object): The instance on which to delete the property.

        Raises:
            AttributeError: If no deleter is defined.
        """
        if self._deleter is None:
            raise AttributeError(f"Can't delete attribute '{self._name}'")
        return self._deleter(instance)

    def setter(self, func):
        """
        Decorator to define a setter for the computed property.

        Args:
            func (function): The setter function.

        Returns:
            ComputedProperty: Self, with the setter assigned.
        """
        self._setter = func
        return self

    def deleter(self, func):
        """
        Decorator to define a deleter for the computed property.

        Args:
            func (function): The deleter function.

        Returns:
            ComputedProperty: Self, with the deleter assigned.
        """
        self._deleter = func
        return self
















