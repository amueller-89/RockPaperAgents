import random
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ValidationError
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


class Slip_Request(BaseModel):
    move: str
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
        db.add(player1)
        db.add(player2)
    elif request.type == "slip":
        game = SlipStrikeDB(date_created=datetime.now())
        db.add(game)
        db.commit()
        player1 = Slip_PlayerDB(user_id=user1.id, game_id=game.id, position=random.randint(0, 4))
        player2 = Slip_PlayerDB(user_id=user2.id, game_id=game.id, position=random.randint(0, 4))
        db.add(player1)
        db.add(player2)
        db.commit()
        game.history = f"The game begins with {player1.user.username} on {player1.position}, and {player2.user.username} on {player2.position}.^"
    else:
        raise ValidationError
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


def commit_move_naive(move: str, who: str, db: Session):
    game = db.query(SlipStrikeDB).first()
    for player in game.players:
        if who == player.user.username:
            # print(f"{who} is actually {player.user.username}")
            active = player
            break
    # print(move)
    active.committed_move_slip = move
    game.last_activity = datetime.now()
    db.commit()
    update(game=game, db=db)


def commit_slip(request: Slip_Request, who: str, db: Session):
    moves = {"r", "l", "0", "1", "2", "3", "4"}
    slips = {"0", "1", "2", "3", "4"}
    attacks = {"K", "P", "R"}
    game = db.query(SlipStrikeDB).filter(SlipStrikeDB.id == request.game_id).first()
    if not game:
        print("no such game")
        return None
    if game.finished:
        print("game finished")
        return None
    active = game.players[0] if game.players[0].user.username == who else game.players[1]
    p2 = game.players[1] if game.players[0].user.username == who else game.players[0]
    if active.hit:
        if len(request.move) != 1 or request.move not in slips:
            print("hit and not syntactically correct")
            return None
        if request.move in active.discarded + active.committed_move_slip + active.cd1 + active.cd2:
            print("hit and the cards not available")
            return None

        if attack(p2.position, int(request.move), p2.committed_move_slip[game.state - 1]):
            print("da schießter hin!")
            return None
        print(f"seems legal, putting {request.move} as slip")
        active.slip = request.move
    else:
        if len(request.move) != 2 or request.move[0] == request.move[1]:
            print("not syntactically correct")
            return None
        for c in request.move:
            if c not in moves | slips | attacks:
                print("invalid character")
                return None
            if c in active.discarded + active.cd1 + active.cd2:
                print("not available")
                return None
        print(f"seems legal, putting {request.move} as move")
        active.committed_move_slip = request.move
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
    print(f"updating {game.type} #{game.id},")
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
        print("start of the round")

        for player in game.players:
            if player.committed_move_slip is None:
                print(f"{player.user.username} has not committed his move")
                return game
        game.history += f"Start of round {game.round}, resolving first card.^"
        for player in game.players:
            player.cd1 = player.cd2
            player.cd2 = ""
        resolve_step(game, game.state)
        if not game.finished:
            game.state = 1
    if game.state == 1:
        print("resolving 2nd card")
        if not resolve_hits(game):
            return game
        game.history += f"Resolving second card.^"
        resolve_step(game, game.state)
        if not game.finished:
            game.state = 2
    if game.state == 2:
        print("resolving hits after 2nd card")
        if not resolve_hits(game):
            return game
        game.history += f"The round ends with {game.players[0].user.username} on {game.players[0].position} and {game.players[1].user.username} on {game.players[1].position}.^"
        game.state = 0
        game.round += 1
        for player in game.players:
            player.committed_move_slip = None
    return game


def resolve_step(game: SlipStrikeDB, card: int):  # 0 - first card, 1 - 2nd card
    p1, p2 = game.players[0], game.players[1]
    moves = {"r", "l", "0", "1", "2", "3", "4"}
    slips = {"0", "1", "2", "3", "4"}
    attacks = {"K", "P", "R"}
    slip_dict = {"K": "knife", "P": "pistol", "R": "rifle"}
    game.history += f"{p1.user.username} reveals {p1.committed_move_slip[card]}.^"
    game.history += f"{p2.user.username} reveals {p2.committed_move_slip[card]}.^"
    # game.history += f"locations before movement: {p1.user.username} on {p1.position}, {p2.user.username} on {p2.position}.^"
    for player in game.players:
        step = player.committed_move_slip[card]
        if step in moves:
            move(player, step)
            if step in slips:
                game.history += f"{player.user.username} slips to tile {player.position}"
                player.cd2 += step
                print(f"adding {step} to cd2, now: {player.cd2}")
            else:
                game.history += f"{player.user.username} steps {'left' if step == 'l' else 'right'} to tile {player.position}.^"
        else:
            game.history += f"{player.user.username} remains on {player.position}.^"
    for player in game.players:
        step = player.committed_move_slip[card]
        if step in attacks:
            opp = p1 if p1 is not player else p2
            game.history += f"{player.user.username} tries to hit with {slip_dict[step]}, "
            if attack(player.position, opp.position, step):
                print(f"{player.user.username} lands a hit with {step}")
                game.history += f"and he lands a hit!^"
                # check for gameover
                print("gameover?")
                available_slips = ""
                print("unavailable: " + opp.discarded + opp.committed_move_slip + opp.cd1 + opp.cd2)
                for s in slips:
                    if s not in opp.discarded + opp.committed_move_slip + opp.cd1 + opp.cd2:
                        print(f"available slip: {s}")
                        if not attack(player.position, int(s), step):
                            available_slips += s
                        else:
                            print("but its attacked!")
                print("slips actually left: " + available_slips)

                if available_slips == "":
                    print(f"{opp.user.username} cannot evade - {player.user.username} wins!")
                    game.history += f"{opp.user.username} cannot evade - {player.user.username} wins!^"
                    game.finished = True
                    player.won = True
                    opp.won = False
                    return game
                game.history += f"{opp.user.username} may slip to {available_slips}.^"
                opp.hit = True
            else:
                game.history += f"but he misses.^"
                print(f"{player.user.username} misses with {step}")
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
            game.history += f"{player.user.username} slips to {player.slip}.^"
            player.hit = None
            player.position = int(player.slip)
            player.discarded += player.slip  # check legality here?
            player.slip = None
    return True
    # now all hits are resolved


def attack(a: int, b: int, weapon: str):
    if weapon == "K" and a == b:
        return True
    if weapon == "P" and a in [(b - 1) % 5, (b + 1) % 5]:
        return True
    if weapon == "R" and a in [(b - 2) % 5, (b + 2) % 5]:
        return True
    return False


def move(player: Slip_PlayerDB, move: str):
    if move == "r":
        player.position = (player.position + 1) % 5
    elif move == "l":
        player.position = (player.position - 1) % 5
    else:
        player.position = int(move)


def update_rps(game: RockPaperScissorsDB):
    for player in game.players:
        if player.committed_move is None:
            # print("not all moves committed")
            return game
    p1, p2 = game.players[0], game.players[1]
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
