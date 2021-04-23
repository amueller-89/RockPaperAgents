from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from models_DB import UserDB, RockPaperScissorsDB, RPS_PlayerDB


##### pydantic models
class Game_Request(BaseModel):
    player1: str
    player2: str
    goal: Optional[int] = 3


class Move_Request(BaseModel):
    move: int
    user_id: Optional[int]
    game_id: int


class Game_Response(BaseModel):
    id: str
    me: str
    opponent: str
    goal: int
    my_score: int
    my_avatar: str
    opponent_score: int
    opponent_avatar: str
    has_moved_opponent: bool
    has_moved_me: bool
    date_created: datetime
    last_activity: Optional[datetime]
    finished: bool


def make_response_from_db(game: RockPaperScissorsDB, my_name: str):
    opponent = ""
    for player in game.players:
        if player.user.username != my_name:
            opponent = player.user.username
            opponent_score = player.score
            opponent_avatar = player.user.avatar
            has_moved_opponent = bool(player.committed_move is not None)
        else:
            my_score = player.score
            my_avatar = player.user.avatar
            has_moved_me = bool(player.committed_move is not None)
    return Game_Response(id=game.id,
                         me=my_name,
                         opponent=opponent,
                         goal=game.goal,
                         my_score=my_score,
                         my_avatar=my_avatar,
                         opponent_score=opponent_score,
                         opponent_avatar=opponent_avatar,
                         has_moved_opponent= has_moved_opponent,
                         has_moved_me=has_moved_me,
                         date_created=game.date_created,
                         last_activity=game.last_activity,
                         finished=game.finished)


##### database utilities
def create_game(rps_request: Game_Request, db: Session):
    user1 = db.query(UserDB).filter(UserDB.username == rps_request.player1).one_or_none()
    user2 = db.query(UserDB).filter(UserDB.username == rps_request.player2).one_or_none()
    if not (user1 and user2):
        return None
    rps = RockPaperScissorsDB(goal=rps_request.goal, date_created=datetime.now())
    db.add(rps)
    db.commit()
    player1 = RPS_PlayerDB(user_id=user1.id, game_id=rps.id)
    player2 = RPS_PlayerDB(user_id=user2.id, game_id=rps.id)
    db.add(player1)
    db.add(player2)
    db.commit()
    return rps


def commit_move(move_request: Move_Request, db: Session):
    game = db.query(RockPaperScissorsDB).filter(RockPaperScissorsDB.id == move_request.game_id).one_or_none()
    if not game:
        return None
    if game.finished:
        return None
    players = game.players  # .filter(RPS_PlayerDB.user_id == move_request.user_id).one_or_none()
    active_player = None
    for player in players:
        if player.user.id == move_request.user_id:
            active_player = player
            break  # TODO check for ill-posed move request?
    active_player.committed_move = move_request.move
    game.last_activity = datetime.now()
    db.commit()
    update(game=game, db=db)
    return game


def update(game: RockPaperScissorsDB, db: Session):
    print(f"updating RPS game# {game.id}")
    if game.finished:
        return game
    for player in game.players:
        if player.committed_move is None:
            # print("not all moves committed")
            return game
    p1, p2 = game.players[0], game.players[1]
    # print("p1 " + p1.user.username + ", p2 " + p2.user.username)
    # print("p1.move " + str(p1.committed_move) + ", p2.move " + str(p2.committed_move))

    if (p1.committed_move - p2.committed_move) % 3 == 0:
        print("TIE")
    if (p1.committed_move - p2.committed_move) % 3 == 1:
        print(p1.user.username + " scores")
        p1.score += 1
    if (p1.committed_move - p2.committed_move) % 3 == 2:
        print(p2.user.username + " scores")
        p2.score += 1
    p1.committed_move = None
    p2.committed_move = None
    for player in game.players:
        if player.score >= game.goal:
            print(player.user.username + " wins RPS#" + str(game.id))
            game.finished = True
            player.won = True
            for player2 in game.players:
                if player2 is not player:
                    player2.won = False  # ugly af
    db.commit()
    return game


def getGames(user: UserDB, db: Session):
    return db.query(RockPaperScissorsDB).join(RPS_PlayerDB).filter(RPS_PlayerDB.user == user)
