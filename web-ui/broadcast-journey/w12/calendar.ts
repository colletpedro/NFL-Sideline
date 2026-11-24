import { teamIdentity } from '../../broadcast-real/identity';
import type { Game } from '../../src/services/types';
import type { CalendarEntry } from './model';
export function calendarGame(e:CalendarEntry):Game {
  const team=(id:string)=>({teamAbbr:id,teamName:teamIdentity(id).city+' '+teamIdentity(id).name,conference:null,division:null,logoUrl:null});
  return {gameId:e.gameId,season:e.season,week:e.week,gameType:e.phase,gameday:e.gameday,awayTeam:team(e.away),homeTeam:team(e.home),awayScore:e.awayScore,homeScore:e.homeScore,result:e.result,
    spreadLine:null,totalLine:null,homeMoneyline:null,awayMoneyline:null,homeSpreadOdds:null,awaySpreadOdds:null,overOdds:null,underOdds:null,roof:null,surface:null,divisionGame:null,updatedAt:null,market:null};
}
