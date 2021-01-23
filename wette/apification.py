from models import Outcome

def apify_challenge(challenge):
    return {'challenge_id': challenge.value,
            'name': challenge.name}

def apify_team(team):
    return {'team_id': team.id,
            'name': team.name,
            'short_name': team.short_name,
            'group': team.group,
            'champion': team.champion,
            'odds': team.odds}


def apify_match(match, include_bets=False):
    d = {'match_id': match.id,
         'date': match.date.isoformat() + 'Z',
         'status': match.status.value,
         'outcome': match.outcome.value if match.outcome is not None else None,
         'team1_name': match.team1.name,
         'team1_goals': match.goals_team1,
         'team2_name': match.team2.name,
         'team2_goals': match.goals_team2,
         'stage': match.stage}

    if not match.editable:
        d['odds'] = {Outcome.TEAM1_WIN.value: match.odds[Outcome.TEAM1_WIN],
                     Outcome.TEAM2_WIN.value: match.odds[Outcome.TEAM2_WIN],
                     Outcome.DRAW.value: match.odds[Outcome.DRAW]}

        # TODO: Check if this is used
        if include_bets:
            d['bets'] = [bet.apify(user=True) for bet in match.bets if bet.user.paid]

    return d


def apify_user(user, include_champion=False, include_bets=False):
    d = {'admin': user.admin,
         'avatar': 'https://api.hello-avatar.com/adorables/400/' + user.name,
         'user_id': user.id,
         'name': user.name,
         'visible_superbets': user.supertips
         }

    if include_champion:
        d['champion'] = apify_team(user.champion) if user.champion is not None else None
        d['champion_correct'] = user.champion_correct

    return d


def apify_bet(bet):
    return {'outcome': bet.outcome.value if bet.outcome is not None else None,
            'superbet': bet.supertip}
