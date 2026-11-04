import {counts,MODEL_SHA,type Play,type Player,type Detail,type Index} from './model';
export function fixture(){
 const play={id:'2026_08_AAA_BBB:1',gameId:'2026_08_AAA_BBB',playId:1,week:8,date:'2026-11-01',team:'AAA',opponent:'BBB',passerId:'00-0000001',name:'Alpha Passer',position:'QB',positionClass:'qb',quarter:1,clock:'10:00',down:2,distance:10,fieldPosition:50,scoreDifferential:0,probability:.1,worthy:true,interception:false,description:'Source evidence',evidence:{source:'Fixture',gameId:'2026_08_AAA_BBB',playId:1}} as Play;
 const plays=[play,{...play,id:'2026_08_AAA_BBB:2',playId:2,worthy:false,probability:.2}];
 const other=[{...play,id:'2026_08_AAA_BBB:3',playId:3,passerId:'00-0000002',name:'Beta Passer',worthy:false,position:null,positionClass:'unknown'}];
 const game={gameId:play.gameId,week:8,date:play.date,home:'BBB',away:'AAA',...counts([...plays,...other])};
 const one:Player={id:play.passerId,name:play.name,teams:['AAA','BBB'],positions:['QB'],positionClass:'qb',...counts(plays),byGame:[{...game,...counts(plays)}]};
 const two:Player={id:other[0].passerId,name:other[0].name,teams:['AAA'],positions:[],positionClass:'unknown',...counts(other),byGame:[{...game,...counts(other)}]};
 const index:Index={schemaVersion:1,packageId:'a'.repeat(24),acquiredAt:'2026-11-04T10:00:00Z',season:2026,phase:'REG',model:{id:'M3-2026-frozen-v2',sha256:MODEL_SHA,structureYears:[2023,2024],calibrationYear:2025,offset:-.1593395890254225},coverage:{games:1,completedGames:2,scheduledGames:270,weeks:[8],pendingGames:[{gameId:'pending',week:8,home:'CCC',away:'DDD',date:play.date,status:'pending',reason:'Charting incompleto'}],scheduled:[],included:[game],pbpWeeks:[8],ftnWeeks:[8]},summary:counts([...plays,...other]),players:[one,two],attribution:'FTN fixture',interpretation:'Experimental'};
 const details:Record<string,Detail>={[one.id]:{packageId:index.packageId,player:one,plays},[two.id]:{packageId:index.packageId,player:two,plays:other}};
 return {index,details,plays};
}
