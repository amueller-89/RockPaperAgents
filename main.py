from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse

from datetime import timedelta
from sqlalchemy.orm import Session

import RPS
from utilities import ACCESS_TOKEN_EXPIRE_MINUTES, get_db, create_access_token, get_current_user, get
from utilities import populate, verify_password, make_message_response_from_db
from utilities import create_message, set_avatar, create_user
from models_pyd import UserPydantic, MessageRequest, OutgoingMessage, RegisterRequest, GameType

from database import engine
from models_DB import UserDB, MessageDB, RockPaperScissorsDB, RPS_PlayerDB
import models_DB

app = FastAPI()

templates = Jinja2Templates(directory="templates")

models_DB.Base.metadata.create_all(bind=engine)

games = [["Rock Paper Scissors", "blue", True], ["Slip Strike", "teal", True],
         ["Indonesian Finger Game", "brown", False], ["Draft Diff", "olive", False]]

games2 = [GameType(name=game[0], color=game[1], active=game[2]) for game in games]


######## HTML endpoints

# SPA babyyyy
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("SPA-dashboard.html", {"request": request})


#  well almost
@app.get("/terms")
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


######## Registration/Authorization endpoints

# check if a given username exists in the database
@app.get("/check_user/{username}")
async def check_user(username: str, db: Session = Depends(get_db)):
    # print(f"{username} exists: {exists}")
    return {
        "code": "success",
        "exists": True if db.query(UserDB).filter(UserDB.username == username).one_or_none() else False
    }


# register a user in the database. should probably handle errors
@app.post("/register")
def register(register_request: RegisterRequest, db: Session = Depends(get_db)):
    # print(f"register request for {register_request.username}, {register_request.password}")
    user = create_user(register_request=register_request, db=db)
    if user:
        return {
            "code": "success",
            "message": "registered user " + user.username + " with password (hashed)" + user.hashed_password +
                       ", plain:" + register_request.password +
                       " and email " + user.email
        }
    else:
        return {
            "code": "error",
            "message": "could NOT register user " + register_request.username
        }


# the frontend asks for JWT token corresponding to given user/pwd combination
@app.post("/token")
async def acquire_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f">>>>>>> acquiring token for {form_data.username} with password {form_data.password}")
    user_db = db.query(UserDB).filter(UserDB.username == form_data.username).one_or_none()
    if not user_db:
        print(">>>>>>>>>>> no such user")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    # print(f">>>>>> verifying {form_data.password} and {user_pyd.hashed_password}")

    verified = verify_password(form_data.password, user_db.hashed_password)
    if not verified:
        print(">>>>>>>>>>> wrong pw")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_db.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


####### public get-endpoints

# returns the (50px*50px, for now) avatar of the given user
@app.get("/avatar/{avatar_name}")
def avatar(avatar_name):
    return FileResponse("images/avatar/" + avatar_name + ".jpg")


# returns a list of available games
@app.get("/games")
def games_available():
    print(games2)
    return games


#######  endpoints restricted to logged in users


# returns the current user (pydantic)
@app.get("/me")
async def me(current_user: UserPydantic = Depends(get_current_user)):
    return current_user  # html response(current_user)?


# returns a list of the last {limit} recent received messages, where limit is a query parameter
@app.get("/myrecentmessages")
async def recent_incoming(limit: int = 5, current_user: UserPydantic = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    me_db = get(current_user.username, db)
    all_queryset = db.query(MessageDB).filter(MessageDB.recipient == me_db)
    ordered_list = all_queryset.order_by(MessageDB.date.desc()).limit(limit).all()
    recents_pyd = [make_message_response_from_db(msg_db) for msg_db in ordered_list]
    return recents_pyd


# TODO probably this should have more query parameters like finished, unfinished, RPS/whatever else we might have...
# error handling lol
# returns the last {limit} active games of the current user
@app.get("/myCurrentGames")
async def recent_games(limit: int = 10, current_user: UserPydantic = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    me = get(current_user.username, db)
    games = RPS.getGames(me, db).filter(RockPaperScissorsDB.finished == False) \
        .order_by(RockPaperScissorsDB.last_activity.desc()).limit(limit).all()
    response = [RPS.make_response_from_db(game=game, my_name=me.username) for game in games]
    return response


# sends a message from the current user
@app.post("/send/")
async def send_message(outgoing: OutgoingMessage, current_user: UserPydantic = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    sender_id = get(current_user.username, db).id
    recipient = get(outgoing.recipient, db)
    if not recipient:
        raise HTTPException(status_code=400, detail="recipient name not found")
    message_request = MessageRequest(sender_id=sender_id, recipient_id=recipient.id, content=outgoing.content)
    create_message(message_request, db)


# sets the current users avatar
@app.put("/myavatar/{name}")
async def choose_avatar(name: str, current_user: UserPydantic = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    user_db = db.query(UserDB).filter(UserDB.username == current_user.username).one_or_none()
    set_avatar(name, user_db, db)
    return {
        "code": "success",
        "message": "put " + name + " as avatar for " + user_db.username
    }


@app.put("/playRPS/")
async def playRPS(game: int, move: int,
                  current_user: UserPydantic = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    move_request = RPS.Move_Request(move=move, user_id=get(current_user.username, db).id, game_id=game)
    if not move_request:
        return {
            "code": "error",
            "message": f"something went wrong creating the move request"
        }
    rps = RPS.commit_move(move_request, db)
    if rps:
        return {
            "code": "success",
            "message": f"committed move {move} for RPS game#{rps.id} for  {current_user.username}"
        }
    else:
        return {
            "code": "error",
            "message": f"something went wrong. likely the game is finished"
        }


@app.post("/createRPS/{opponent}")
async def createRPS(opponent: str, goal: Optional[int] = None,
                    current_user: UserPydantic = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    game_request = RPS.Game_Request(player1=current_user.username, player2=opponent, goal=goal)
    rps = RPS.create_game(game_request, db)
    if rps:
        return {
            "code": "success",
            "message": f"created new RPS game#{rps.id},  {current_user.username} vs {opponent}, first to {rps.goal}"
        }
    else:
        return {
            "code": "error",
            "message": f"something went wrong"
        }


#######################################
###### testing
@app.get("/test1")
def test_db(db: Session = Depends(get_db)):
    populate(db)


@app.get("/test2")
def test2():
    pass


######## no longer in use. templates might have been moved!
@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/rps")
def home(request: Request):
    # print(request)
    return templates.TemplateResponse("rps.html", {"request": request})


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
