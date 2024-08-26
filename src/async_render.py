'''
Copyright 2024 ITProjects

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Represents an asynchronous worker.

An async worker's job is to run a blocking operation in the background,
using a Gio.Task to avoid blocking the app's main thread and freezing
the user interface.

The terminology used here is closely related to the Gio.Task API.

There are two ways to specify the operation that should be run in the background:

1. By passing the blocking operation (a function or method) to the constructor.
2. By defining the work() method in a subclass.

Constructor parameters:

OPERATION (callable)
    The function or method that needs to be run asynchronously.
    This is only necessary when using a direct instance of AsyncWorker,
    not when using an instance of a subclass of AsyncWorker, in which case
    an AsyncWorker.work() method must be defined by the subclass instead.

OPERATION_INPUTS (tuple)
    Input data for OPERATION, if any.

OPERATION_CALLBACK (callable)
    A function or method to call when the OPERATION is complete.

OPERATION_CALLBACK_INPUTS (tuple)
    Optional. Additional input data for OPERATION_CALLBACK.

CANCELLABLE (Gio.Cancellable)
    Optional. It defaults to None, meaning that the blocking operation is not cancellable.

The content of this file was originally taken from the post:
discourse.gnome.org/t/how-do-you-run-a-blocking-method-asynchronously-with-gio-task-in-a-python-gtk-app/10651
'''

import gi
from gi.repository import Gio, GObject

class AsyncWorker(GObject.Object):

    def __init__(
            self,
            operation=None,
            operation_inputs=(),
            operation_callback=None,
            operation_callback_inputs=(),
            cancellable=None
    ):
        super().__init__()
        self.operation = operation
        self.operation_inputs = operation_inputs
        self.operation_callback = operation_callback
        self.operation_callback_inputs = operation_callback_inputs
        self.cancellable = cancellable

        # Holds the actual data referenced from the Gio.Task
        # created in the AsyncWorker.start method.
        self.pool = {}

    def start(self):
        '''
        Schedule the blocking operation to be run asynchronously.

        The blocking operation is either self.operation or self.work,
        depending on how the AsyncWorker was instantiated.

        This method corresponds to the function referred to as
        'blocking_function_async' in GNOME Developer documentation.
        '''
        task = Gio.Task.new(
            self,
            self.cancellable,
            self.operation_callback,
            self.operation_callback_inputs
        )

        if self.cancellable is None:
            task.set_return_on_cancel(False)

        data_id = id(self.operation_inputs)
        self.pool[data_id] = self.operation_inputs
        task.set_task_data(
            data_id,
            # Note: Data destroyer function always gets None as argument.
            #
            # This function is supposed to take as an argument,
            # the same value passed, as data_id to task.set_task_data,
            # but when the destroyer function is called, it seems
            # it always gets None as an argument instead.
            # That's why the 'key' parameter is not being used in
            # the body of the anonymous function.
            lambda key: self.pool.pop(data_id)
        )

        task.run_in_thread(self._thread_callback)

    def _thread_callback(self, task, worker, task_data, cancellable):
        # Run the blocking operation in a worker thread.
        # task_data is always None for Gio.Task.run_in_thread callback.
        #
        # The value passed to this callback as task_data always seems to be None,
        # so we get the data for the blocking operation as follows instead.
        data_id = task.get_task_data()
        data = self.pool.get(data_id)

        # Run the blocking operation.
        if self.operation is None: # Assume AsyncWorker was extended.
            outcome = self.work(*data)
        else: # Assume AsyncWorker was instantiated directly.
            outcome = self.operation(*data)

        task.return_value(outcome)

    def return_value(self, result):
        '''
        Return the value of the operation that was run asynchronously.

        This method corresponds to the function referred to as
        'blocking_function_finish' in GNOME Developer documentation.

        This method is called from the view where the asynchronous
        operation is started to update the user interface according
        to the resulting value.

        RESULT (Gio.AsyncResult)
          The asyncronous result of the asynchronous blocking operation.

        RETURN VALUE (object)
          Any of the return values of the blocking operation.
          If RESULT turns out to be invalid, return an error dictionary in the form:

          {'AsyncWorkerError': 'Gio.Task.is_valid returned False.'}
        '''
        value = None

        if Gio.Task.is_valid(result, self):
            return None
            #value = result.propagate_value().value
        else:
            error = 'Gio.Task.is_valid returned False.'
            value = {'AsyncWorkerError': error}

        return value
