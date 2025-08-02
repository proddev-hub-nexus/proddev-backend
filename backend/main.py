from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def root():
    return "I am a fastapi app"