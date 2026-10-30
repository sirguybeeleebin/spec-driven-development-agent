# Task

- task_id: 006_main
- target_file: main.py
- target_test_file: main_test.py

# Goal

Wire the whole application at module scope: build the three repositories, the checkout service, and the orders router inside a startup lifecycle; open one in-memory connection on startup and close it on shutdown.

# Declares

- lifespan
- app

# Interfaces

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the application lifecycle.

    Description:
        Open one shared in-memory connection, apply the schema,
        build the three repositories, the checkout service, and
        the orders router on startup; close the connection on
        shutdown. The shutdown path runs even when startup fails
        after the connection was opened.

    Steps:
        1. On startup, open one shared connection to `:memory:`,
           configured so it can be used from any thread.
        2. Apply the schema to that connection.
        3. Build the three repositories over the connection.
        4. Build the checkout service over the three
           repositories.
        5. Attach exactly one router to the application, closed
           over the service.
        6. Yield control so the application serves requests.
        7. On shutdown, close the shared connection inside a
           finalizer that runs even when startup fails after the
           connection was opened.
        8. Let any storage error from connect or schema loading
           propagate unchanged. Let any framework error from
           startup propagate unchanged.
    """
    ...
```

```python
app: FastAPI = FastAPI(
    title="Shop",
    version="0.1.0",
    lifespan=lifespan,
)
```

# Gherkins

## lifespan: app starts and applies schema

```gherkin
Given the application module and its lifespan
When the lifespan is entered via a test client context manager
Then the storage catalog contains the tables products, orders, order_lines
And reading an unknown order returns 404
```