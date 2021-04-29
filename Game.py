from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from models_DB import UserDB, RockPaperScissorsDB, RPS_PlayerDB, GameDB, Slip_PlayerDB, SlipStrikeDB, PlayerDB


##### pydantic models
class Game_Request(BaseModel):
    player1: str
    player2: str
    type: str
    goal: Optional[int] = 3


class Move_Request(BaseModel):
    move: int
    user_id: Optional[int]
    game_id: int


class Game_Response(BaseModel):
    type: str
    id: str
    me: str
    opponent: str
    my_avatar: str
    opponent_avatar: str
    has_moved_opponent: bool
    has_moved_me: bool
    my_history: str
    opponent_history: str
    date_created: datetime
    last_activity: Optional[datetime]
    finished: bool
    won: Optional[bool]
    history: str


class RPS_Response(Game_Response):
    goal: int
    my_score: int
    opponent_score: int


class Slip_Response(Game_Response):
    pass
    # discarded him/me etc etc


def make_response_from_db(game: GameDB, my_name: str):
    response_dict = {"me": my_name, "type": game.type, "id": game.id, "date_created": game.date_created,
                     "last_activity": game.last_activity, "finished": game.finished, "history": game.history}
    for player in game.players:
        if player.user.username == my_name:
            response_dict["my_avatar"] = player.user.avatar
            response_dict["my_history"] = player.moves
            response_dict["won"] = player.won

            if game.type == "rps":
                response_dict["my_score"] = player.score
                response_dict["has_moved_me"] = bool(player.committed_move is not None)

            if game.type == "slip":
                response_dict["has_moved_me"] = bool(player.committed_move_slip is not None)
        else:
            response_dict["opponent"] = player.user.username
            response_dict["opponent_avatar"] = player.user.avatar
            response_dict["opponent_history"] = player.moves

            if game.type == "rps":
                response_dict["opponent_score"] = player.score
                response_dict["has_moved_opponent"] = bool(player.committed_move is not None)

            if game.type == "slip":
                response_dict["has_moved_opponent"] = bool(player.committed_move_slip is not None)

    if game.type == "rps":
        response_dict["goal"] = game.goal
        return RPS_Response(**response_dict)
    if game.type == "slip":
        response = Slip_Response(**response_dict)
        return response


#  deprecated
# def make_response_from_db2(game: GameDB, my_name: str):
#     opponent = ""
#     opponent_history = "",
#     my_history = "",
#     for player in game.players:
#         if player.user.username != my_name:
#             opponent = player.user.username
#             opponent_avatar = player.user.avatar
#             opponent_history = player.moves
#             if game.type == "rps":
#                 opponent_score = player.score
#                 has_moved_opponent = bool(player.committed_move is not None)
#         else:
#             my_avatar = player.user.avatar
#             my_history = player.moves
#             if game.type == "rps":
#                 has_moved_me = bool(player.committed_move is not None)
#                 my_score = player.score
#     if game.type == "rps":
#         goal = game.goal
#     return RPS_Response(type=game.type,
#                         id=game.id,
#                         me=my_name,
#                         opponent=opponent,
#                         goal=goal,
#                         my_score=my_score,
#                         my_avatar=my_avatar,
#                         opponent_score=opponent_score,
#                         opponent_avatar=opponent_avatar,
#                         my_history=my_history,
#                         opponent_history=opponent_history,
#                         has_moved_opponent=has_moved_opponent,
#                         has_moved_me=has_moved_me,
#                         date_created=game.date_created,
#                         last_activity=game.last_activity,
#                         finished=game.finished)


##### database utilities
def create_game(request: Game_Request, db: Session):
    if not request:
        print("im not creating from null")
        return None
    user1 = db.query(UserDB).filter(UserDB.username == request.player1).one_or_none()
    user2 = db.query(UserDB).filter(UserDB.username == request.player2).one_or_none()
    if not (user1 and user2):
        return None
    if request.type == "rps":
        game = RockPaperScissorsDB(goal=request.goal, date_created=datetime.now())
        db.add(game)
        db.commit()
        player1 = RPS_PlayerDB(user_id=user1.id, game_id=game.id)
        player2 = RPS_PlayerDB(user_id=user2.id, game_id=game.id)
    if request.type == "slip":
        game = SlipStrikeDB(date_created=datetime.now())
        db.add(game)
        db.commit()
        player1 = Slip_PlayerDB(user_id=user1.id, game_id=game.id)
        player2 = Slip_PlayerDB(user_id=user2.id, game_id=game.id)
    db.add(player1)
    db.add(player2)
    db.commit()
    return game


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


def resign(id: int, me: str, db: Session):
    print(f"resigning game#{id} for {me}")
    game = db.query(GameDB).filter(GameDB.id == id).one_or_none()
    print(type(game))
    if not game:
        return
    for player in game.players:
        if player.user.username != me:
            game.history += f" {me} resigns."
            game.history += f" {player.user.username} wins!."
            player.won = True
        else:
            player.won = False
    game.finished = True
    db.commit()
    return game


def update(game: GameDB, db: Session):
    print(f"updating {game.type}# {game.id},")
    if game.finished:
        return game
    if game.type == "rps":
        update_rps(game)
    if game.type == "slip":
        update_slip(game)
    db.commit()
    return game


def update_slip(game: SlipStrikeDB):
    if game.state == 0:
        for player in game.players:
            if player.committed_move_slip is None:
                print(f"{player.user.username} has not committed his move")
                return game
        for player in game.players:
            player.cd1 = player.cd2
            player.cd2 = ""
        resolve_step(game, game.state)
        game.state = 1
        update_slip(game)
    if game.state == 1:
        if not resolve_hits():
            return game
        resolve_step(game, game.state)
        game.state = 2
        update_slip()
    if game.state == 2:
        if not resolve_hits():
            return game
        game.state = 0
        for player in game.players:
            player.committed_move_slip = None



def resolve_step(game: SlipStrikeDB, card: int):  # 0 - first card, 1 - 2nd card
    p1, p2 = game.players[0], game.players[1]
    moves = {"r", "l", "0", "1", "2", "3", "4"}
    slips = {"0", "1", "2", "3", "4"}
    attacks = {"K", "P", "R"}
    print("locations before movement:")
    print(p1.position, p2.position)
    for player in game.players:
        step = player.committed_move_slip[card]
        if step in moves:
            move(player, step)
            if step in slips:
                player.cd2 += player.step
                print(f"adding {step} to cd2, now: {player.cd2}")
    print("locations after movement:")
    print(p1.position, p2.position)
    for player in game.players:
        step = player.committed_move_slip[card]
        if step in attacks:
            if attack(player, p1 if p1 is not player else p2, step):
                print(f"{player.user.username} lands a hit with {step}")
                p1 if p1 is not player else p2.hit = True
        player.cd1 += step




def resolve_hits(game: SlipStrikeDB):
    hit_and_no_slip = False
    for player in game.players:
        if player.hit:
            if not player.slip:
                hit_and_no_slip = True
    if hit_and_no_slip:
        print("someone hit has not committed a slip")
        return False

    for player in game.players:
        if player.hit:
            print(f"{player.user.username} slips to evade, new position {player.slip}")
            player.hit = None
            player.position = int(player.slip)
            player.discarded += player.slip  # check legality here?
            player.slip = None
    return True
    # now all hits are resolved


def attack(a: Slip_PlayerDB, b: Slip_PlayerDB, weapon: str):
    if weapon == "K" and a.position == b.position:
        return True
    if weapon == "P" and a.position in [(b.position - 1) % 5, (b.position + 1) % 5]:
        return True
    if weapon == "R" and a.position in [(b.position - 2) % 5, (b.position + 2) % 5]:
        return True
    return False


def move(player: Slip_PlayerDB, move: str):
    if player.committed_move[0] == "r":
        player.position = (player.position + 1) % 5
    if player.committed_move[0] == "l":
        player.position = (player.position - 1) % 5
    else:
        player.position = int(move)


def update_rps(game: RockPaperScissorsDB):
    for player in game.players:
        if player.committed_move is None:
            # print("not all moves committed")
            return game
    p1, p2 = game.players[0], game.players[1]
    # print("p1 " + p1.user.username + ", p2 " + p2.user.username)
    # print("p1.move " + str(p1.committed_move) + ", p2.move " + str(p2.committed_move))
    move_dict = {0: "rock", 1: "paper", 2: "scissors"}

    game.history += f" {p1.user.username} plays {move_dict[p1.committed_move]}, {p2.user.username} plays {move_dict[p2.committed_move]}."
    if (p1.committed_move - p2.committed_move) % 3 == 0:
        print("TIE")
        game.history += " No one scores!"
    if (p1.committed_move - p2.committed_move) % 3 == 1:
        print(p1.user.username + " scores.")
        game.history += f" {p1.user.username} scores!"
        p1.score += 1
    if (p1.committed_move - p2.committed_move) % 3 == 2:
        print(p2.user.username + " scores")
        game.history += f" {p2.user.username} scores!"
        p2.score += 1
    p1.moves += str(p1.committed_move)
    p2.moves += str(p2.committed_move)
    p1.committed_move = None
    p2.committed_move = None
    for player in game.players:
        if player.score >= game.goal:
            print(player.user.username + " wins RPS#" + str(game.id))
            game.history += f" {player.user.username} wins!"
            game.finished = True
            player.won = True
            for player2 in game.players:
                if player2 is not player:
                    player2.won = False  # ugly af


def getGames(user: UserDB, db: Session):
    return db.query(GameDB).join(PlayerDB).filter(PlayerDB.user == user)
