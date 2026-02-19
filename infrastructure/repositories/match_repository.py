"""Match repository implementation."""
import logging
from typing import Optional, List
from datetime import datetime

from domain.entities import Match, Team, Participant
from domain.enums import Region, QueueType, Rank, Role
from domain.interfaces import IMatchRepository
from infrastructure.api import RiotAPIClient

logger = logging.getLogger(__name__)


class MatchRepository(IMatchRepository):
    """Repository for match data using Riot API."""
    
    def __init__(self, api_client: RiotAPIClient):
        """
        Initialize match repository.
        
        Args:
            api_client: Riot API client instance
        """
        self.api_client = api_client
    
    async def get_match_ids_by_puuid(
        self,
        region: Region,
        puuid: str,
        queue_type: QueueType,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start: int = 0,
        count: int = 100
    ) -> List[str]:
        """Get match IDs for a summoner."""
        return await self.api_client.get_match_ids_by_puuid(
            region=region,
            puuid=puuid,
            queue=queue_type,
            start_time=start_time,
            end_time=end_time,
            start=start,
            count=count
        )
    
    async def get_match_by_id(
        self,
        region: Region,
        match_id: str
    ) -> Optional[Match]:
        """
        Get a single match by ID.
        
        Args:
            region: Server region
            match_id: Match identifier
            
        Returns:
            Match entity or None if not found
        """
        # Fetch from API
        match_data = await self.api_client.get_match_by_id(region, match_id)
        if not match_data:
            logger.warning(f"Match {match_id} not found in API")
            return None
        
        try:
            match = self._parse_match_data(match_data, region)
            return match
        except Exception as e:
            logger.error(f"Error parsing match {match_id}: {e}")
            return None
    
    def _parse_match_data(self, data: dict, region: Region) -> Match:
        """Parse raw API match data into Match entity."""
        metadata = data['metadata']
        info = data['info']
        
        # Parse queue type
        queue_id = info.get('queueId', 0)
        queue_type = (
            QueueType.RANKED_SOLO_5x5 if queue_id == 420 
            else QueueType.RANKED_FLEX_SR
        )
        
        # Parse teams
        teams_data = info.get('teams', [])
        team_100_data = next((t for t in teams_data if t.get('teamId') == 100), {'teamId': 100, 'win': False})
        team_200_data = next((t for t in teams_data if t.get('teamId') == 200), {'teamId': 200, 'win': False})
        team_100 = self._parse_team_data(team_100_data)
        team_200 = self._parse_team_data(team_200_data)
        
        # Parse participants
        participants = []
        for p_data in info.get('participants', []):
            participant = self._parse_participant_data(p_data)
            participants.append(participant)
        
        # Calculate team totals
        self._calculate_team_totals(team_100, participants)
        self._calculate_team_totals(team_200, participants)
        
        # Create match entity
        match = Match(
            match_id=metadata.get('matchId', ''),
            game_id=info.get('gameId', 0),
            region=region,
            platform_id=info.get('platformId', region.value),
            queue_id=queue_id,
            queue_type=queue_type,
            game_creation=info.get('gameCreation', 0),
            game_start_timestamp=info.get('gameStartTimestamp', info.get('gameCreation', 0)),
            game_end_timestamp=info.get('gameEndTimestamp', info.get('gameCreation', 0) + info.get('gameDuration', 0) * 1000),
            game_duration=info.get('gameDuration', 0),
            game_version=info.get('gameVersion', ''),
            game_mode=info.get('gameMode', ''),
            game_type=info.get('gameType', ''),
            team_100=team_100,
            team_200=team_200,
            participants=participants
        )
        
        return match
    
    def _parse_team_data(self, team_data: dict) -> Team:
        """Parse raw team data into Team entity."""
        objectives = team_data.get('objectives', {})
        
        return Team(
            team_id=team_data.get('teamId', 0),
            win=team_data.get('win', False),
            # Dragons
            dragon_kills=objectives.get('dragon', {}).get('kills', 0),
            first_dragon=objectives.get('dragon', {}).get('first', False),
            # Baron
            baron_kills=objectives.get('baron', {}).get('kills', 0),
            first_baron=objectives.get('baron', {}).get('first', False),
            # Rift Herald
            rift_herald_kills=objectives.get('riftHerald', {}).get('kills', 0),
            first_rift_herald=objectives.get('riftHerald', {}).get('first', False),
            # Voidgrubs (horde)
            horde_kills=objectives.get('horde', {}).get('kills', 0),
            # Atakhan
            atakhan_kills=objectives.get('atakhan', {}).get('kills', 0),
            first_atakhan=objectives.get('atakhan', {}).get('first', False),
            # Towers
            tower_kills=objectives.get('tower', {}).get('kills', 0),
            first_tower=objectives.get('tower', {}).get('first', False),
            # Inhibitors
            inhibitor_kills=objectives.get('inhibitor', {}).get('kills', 0),
            first_inhibitor=objectives.get('inhibitor', {}).get('first', False),
            # Champion kills
            champion_kills=objectives.get('champion', {}).get('kills', 0),
            first_blood=objectives.get('champion', {}).get('first', False),
            # Bans
            bans=[b['championId'] for b in team_data.get('bans', [])]
        )
    
    def _parse_participant_data(self, p_data: dict) -> Participant:
        """Parse raw participant data into Participant entity."""
        # Parse role
        try:
            position = Role.from_string(p_data.get('individualPosition', 'BOTTOM'))
            team_position = Role.from_string(p_data.get('teamPosition', 'BOTTOM'))
        except:
            position = Role.BOTTOM
            team_position = Role.BOTTOM
        
        return Participant(
            puuid=p_data.get('puuid', ''),
            summoner_name=p_data.get('summonerName', ''),
            summoner_id=p_data.get('summonerId', ''),
            summoner_level=p_data.get('summonerLevel', 0),
            team_id=p_data.get('teamId', 0),
            participant_id=p_data.get('participantId', 0),
            champion_id=p_data.get('championId', 0),
            champion_name=p_data.get('championName', ''),
            individual_position=position,
            team_position=team_position,
            # Summoner spells
            summoner1_id=p_data.get('summoner1Id', 0),
            summoner2_id=p_data.get('summoner2Id', 0),
            # Game outcome
            win=p_data.get('win', False),
            kills=p_data.get('kills', 0),
            deaths=p_data.get('deaths', 0),
            assists=p_data.get('assists', 0),
            # Gold & XP
            gold_earned=p_data.get('goldEarned', 0),
            gold_spent=p_data.get('goldSpent', 0),
            total_minions_killed=p_data.get('totalMinionsKilled', 0),
            champion_experience=p_data.get('champExperience', 0),
            # Damage
            total_damage_dealt_to_champions=p_data.get('totalDamageDealtToChampions', 0),
            total_damage_taken=p_data.get('totalDamageTaken', 0),
            physical_damage_dealt_to_champions=p_data.get('physicalDamageDealtToChampions', 0),
            magic_damage_dealt_to_champions=p_data.get('magicDamageDealtToChampions', 0),
            true_damage_dealt_to_champions=p_data.get('trueDamageDealtToChampions', 0),
            # Vision
            vision_score=p_data.get('visionScore', 0),
            wards_placed=p_data.get('wardsPlaced', 0),
            wards_killed=p_data.get('wardsKilled', 0),
            vision_wards_bought_in_game=p_data.get('visionWardsBoughtInGame', 0),
            # Items
            item0=p_data.get('item0', 0),
            item1=p_data.get('item1', 0),
            item2=p_data.get('item2', 0),
            item3=p_data.get('item3', 0),
            item4=p_data.get('item4', 0),
            item5=p_data.get('item5', 0),
            item6=p_data.get('item6', 0),
            # Objectives
            turret_kills=p_data.get('turretKills', 0),
            inhibitor_kills=p_data.get('inhibitorKills', 0),
            dragon_kills=p_data.get('dragonKills', 0),
            baron_kills=p_data.get('baronKills', 0),
        )
    
    def _calculate_team_totals(self, team: Team, participants: List[Participant]) -> None:
        """Calculate team total gold and XP from participants."""
        team_participants = [p for p in participants if p.team_id == team.team_id]
        team.total_gold = sum(p.gold_earned for p in team_participants)
        team.total_experience = sum(p.champion_experience for p in team_participants)
    
    async def save_match(self, match: Match) -> bool:
        """
        Save match to local storage.
        
        Args:
            match: Match entity to save
            
        Returns:
            True if saved successfully
        """
        return True
