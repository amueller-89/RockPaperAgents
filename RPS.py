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
    user_id: int
    game_id: int


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


def update(game: RockPaperScissorsDB, db: Session):
    print("updating RPS game#", game.id)
    if game.finished:
        return
    for player in game.players:
        if player.committed_move is None:
            # print("not all moves committed")
            return
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
                    player2.won = False             # ugly af
    db.commit()


def getGames(user: UserDB, db: Session):
    return db.query(RockPaperScissorsDB).join(RPS_PlayerDB).filter(RPS_PlayerDB.user == user)