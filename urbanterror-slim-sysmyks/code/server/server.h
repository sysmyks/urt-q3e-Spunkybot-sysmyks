/*
===========================================================================
Copyright (C) 1999-2005 Id Software, Inc.

This file is part of Quake III Arena source code.

Quake III Arena source code is free software; you can redistribute it
and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

Quake III Arena source code is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Quake III Arena source code; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
===========================================================================
*/
// server.h

#include "../qcommon/q_shared.h"
#include "../qcommon/qcommon.h"
#include "../qcommon/vm_local.h"
#include "../game/g_public.h"
#include "../game/bg_public.h"

//=============================================================================

#define	PERS_SCORE				0		// !!! MUST NOT CHANGE, SERVER AND
										// GAME BOTH REFERENCE !!!

#define	MAX_ENT_CLUSTERS	16

typedef struct svEntity_s {
	struct worldSector_s *worldSector;
	struct svEntity_s *nextEntityInWorldSector;

	entityState_t	baseline;		// for delta compression of initial sighting
	int			numClusters;		// if -1, use headnode instead
	int			clusternums[MAX_ENT_CLUSTERS];
	int			lastCluster;		// if all the clusters don't fit in clusternums
	int			areanum, areanum2;
	int			snapshotCounter;	// used to prevent double adding from portal views
} svEntity_t;

typedef enum {
	SS_DEAD,			// no map loaded
	SS_LOADING,			// spawning level entities
	SS_GAME				// actively running
} serverState_t;

// we might not use all MAX_GENTITIES every frame
// so leave more room for slow-snaps clients etc.
#define NUM_SNAPSHOT_FRAMES (PACKET_BACKUP*4)

typedef struct snapshotFrame_s {
	entityState_t *ents[ MAX_GENTITIES ];
	int	frameNum;
	int start;
	int count;
} snapshotFrame_t;

typedef struct {
	serverState_t	state;
	qboolean		restarting;			// if true, send configstring changes during SS_LOADING
	int				serverId;			// changes each server start
	int				restartedServerId;	// serverId before a map_restart
	int				checksumFeed;		// the feed key that we use to compute the pure checksum strings
	// https://zerowing.idsoftware.com/bugzilla/show_bug.cgi?id=475
	// the serverId associated with the current checksumFeed (always <= serverId)
	int				checksumFeedServerId;
	int				snapshotCounter;	// incremented for each snapshot built
	int				timeResidual;		// <= 1000 / sv_frame->value
	char			*configstrings[MAX_CONFIGSTRINGS];
	svEntity_t		svEntities[MAX_GENTITIES];

	const char		*entityParsePoint;	// used during game VM init

	// the game virtual machine will update these on init and changes
	sharedEntity_t	*gentities;
	int				gentitySize;
	int				num_entities;		// current number, <= MAX_GENTITIES

	playerState_t	*gameClients;
	int				gameClientSize;		// will be > sizeof(playerState_t) due to game private data

	int				restartTime;
	int				time;

	byte			baselineUsed[ MAX_GENTITIES ];
} server_t;

typedef struct {
	int				areabytes;
	byte			areabits[MAX_MAP_AREA_BYTES];		// portalarea visibility bits
	playerState_t	ps;
	int				num_entities;
#if 0
	int				first_entity;		// into the circular sv_packet_entities[]
										// the entities MUST be in increasing state number
										// order, otherwise the delta compression will fail
#endif
	int				messageSent;		// time the message was transmitted
	int				messageAcked;		// time the message was acked
	int				messageSize;		// used to rate drop packets

	int				frameNum;			// from snapshot storage to compare with last valid
	entityState_t	*ents[ MAX_SNAPSHOT_ENTITIES ];

} clientSnapshot_t;

typedef enum {
	CS_FREE = 0,	// can be reused for a new connection
	CS_ZOMBIE,		// client has been disconnected, but don't reuse
					// connection for a couple seconds
	CS_CONNECTED,	// has been assigned to a client_t, but no gamestate yet
	CS_PRIMED,		// gamestate has been sent, but client hasn't sent a usercmd
	CS_ACTIVE		// client is fully in game
} clientState_t;

typedef enum {
    OFFSET_PS_HEALTH,
    OFFSET_PS_STAMINA,
	OFFSET_PS_MAX,
} playerStateOffsets_t;


typedef struct netchan_buffer_s {
	msg_t           msg;
	byte            msgBuffer[MAX_MSGLEN];
	char		clientCommandString[MAX_STRING_CHARS];	// valid command string for SV_Netchan_Encode
	struct netchan_buffer_s *next;
} netchan_buffer_t;

typedef struct rateLimit_s {
	int			lastTime;
	int			burst;
} rateLimit_t;

typedef struct leakyBucket_s leakyBucket_t;
struct leakyBucket_s {
	netadrtype_t	type;

	union {
		byte	_4[4];
		byte	_6[16];
	} ipv;

	rateLimit_t rate;

	int			hash;
	int			toxic;

	leakyBucket_t *prev, *next;
};

typedef struct {
	vec3_t savedPosition;      // Saved position for /load command
	vec3_t savedPositionAngle; // Saved angles for /load command
	qboolean ghost;
	int infiniteStamina;
} clientMove_t;

typedef struct client_s {
	clientState_t	state;
	char			userinfo[MAX_INFO_STRING];		// name, etc

	char			reliableCommands[MAX_RELIABLE_COMMANDS][MAX_STRING_CHARS];
	int				reliableSequence;		// last added reliable message, not necessarily sent or acknowledged yet
	int				reliableAcknowledge;	// last acknowledged reliable message
	int				messageAcknowledge;

	int				gamestateMessageNum;	// netchan->outgoingSequence of gamestate
	int				challenge;

	usercmd_t		lastUsercmd;
	int				lastClientCommand;	// reliable client message sequence
	char			lastClientCommandString[MAX_STRING_CHARS];
	sharedEntity_t	*gentity;			// SV_GentityNum(clientnum)
	char			name[MAX_NAME_LENGTH];			// extracted from userinfo, high bits masked

	// downloading
	char			downloadName[MAX_QPATH]; // if not empty string, we are downloading
	fileHandle_t	download;			// file being downloaded
 	int				downloadSize;		// total bytes (can't use EOF because of paks)
 	int				downloadCount;		// bytes sent
	int				downloadClientBlock;	// last block we sent to the client, awaiting ack
	int				downloadCurrentBlock;	// current block number
	int				downloadXmitBlock;	// last block we xmited
	unsigned char	*downloadBlocks[MAX_DOWNLOAD_WINDOW];	// the buffers for the download blocks
	int				downloadBlockSize[MAX_DOWNLOAD_WINDOW];
	qboolean		downloadEOF;		// We have sent the EOF block
	int				downloadSendTime;	// time we last got an ack from the client

	int				deltaMessage;		// frame last client usercmd message
	int				lastPacketTime;		// svs.time when packet was last received
	int				lastConnectTime;	// svs.time when connection started
	int				lastDisconnectTime;
	int				lastSnapshotTime;	// svs.time of last sent snapshot
	qboolean		rateDelayed;		// true if nextSnapshotTime was set based on rate instead of snapshotMsec
	int				timeoutCount;		// must timeout a few frames in a row so debugging doesn't break
	clientSnapshot_t	frames[PACKET_BACKUP];	// updates can be delta'd from here
	int				ping;
	int				rate;				// bytes / second, 0 - unlimited
	int				snapshotMsec;		// requests a snapshot every snapshotMsec unless rate choked
	qboolean		pureAuthentic;
	qboolean		gotCP;				// TTimo - additional flag to distinguish between a bad pure checksum, and no cp command at all
	netchan_t		netchan;
	// TTimo
	// queuing outgoing fragmented messages to send them properly, without udp packet bursts
	// in case large fragmented messages are stacking up
	// buffer them into this queue, and hand them out to netchan as needed
	netchan_buffer_t *netchan_start_queue;
	netchan_buffer_t **netchan_end_queue;

	int				oldServerTime;
	qboolean		csUpdated[MAX_CONFIGSTRINGS];
	qboolean		compat;

	// flood protection
	rateLimit_t		cmd_rate;
	rateLimit_t		info_rate;
	rateLimit_t		gamestate_rate;

	// client can decode long strings
	qboolean		longstr;

	qboolean		justConnected;

	char			tld[3]; // "XX\0"
	const char		*country;

	//sysmyks	
	qboolean isReady;
	qboolean isRunning;
	clientMove_t cm;
	
#ifdef USE_AUTH
	char auth[MAX_NAME_LENGTH];
#endif
} client_t;

typedef struct {
    qboolean detected;
    char playerName[MAX_NAME_LENGTH];
    int startTime;
    int clientNum;
} courseDetection_t;


// MAX_CHALLENGES is made large to prevent a denial
// of service attack that could cycle all of them
// out before legitimate users connected
#define	MAX_CHALLENGES	2048
// Allow a certain amount of challenges to have the same IP address
// to make it a bit harder to DOS one single IP address from connecting
// while not allowing a single ip to grab all challenge resources
#define MAX_CHALLENGES_MULTI (MAX_CHALLENGES / 2)

typedef struct {
	netadr_t	adr;
	int			challenge;
	int			clientChallenge;		// challenge number coming from the client
	int			time;				// time the last packet was sent to the autherize server
	int			pingTime;			// time the challenge response was sent to client
	qboolean	wasrefused;
	qboolean	connected;
} challenge_t;

//=============================================================================


// this structure will be cleared only when the game dll changes
typedef struct {
	qboolean	initialized;				// sv_init has completed

	int			time;						// will be strictly increasing across level changes
	int			msgTime;					// will be used as precise sent time

	int			snapFlagServerBit;			// ^= SNAPFLAG_SERVERCOUNT every SV_SpawnServer()

	client_t	*clients;					// [sv_maxclients->integer];
	int			numSnapshotEntities;		// PACKET_BACKUP*MAX_SNAPSHOT_ENTITIES
	entityState_t	*snapshotEntities;		// [numSnapshotEntities]
	int			nextHeartbeatTime;

	netadr_t	authorizeAddress;			// for rcon return messages
	int			masterResolveTime[MAX_MASTER_SERVERS]; // next svs.time that server should do dns lookup for master server
	challenge_t	challenges[MAX_CHALLENGES];

	// common snapshot storage
	int			freeStorageEntities;
	int			currentStoragePosition;	// next snapshotEntities to use
	int			snapshotFrame;			// incremented with each common snapshot built
	int			currentSnapshotFrame;	// for initializing empty frames
	int			lastValidFrame;			// updated with each snapshot built
	snapshotFrame_t	snapFrames[ NUM_SNAPSHOT_FRAMES ];
	snapshotFrame_t	*currFrame; // current frame that clients can refer

} serverStatic_t;

#ifdef USE_BANS
#define SERVER_MAXBANS	1024
// Structure for managing bans
typedef struct
{
	netadr_t ip;
	// For a CIDR-Notation type suffix
	int subnet;

	qboolean isexception;
} serverBan_t;
#endif

//=============================================================================

extern	serverStatic_t	svs;				// persistant server info across maps
extern	server_t		sv;					// cleared each map
extern	vm_t			*gvm;				// game virtual machine

extern	cvar_t	*sv_fps;
extern	cvar_t	*sv_timeout;
extern	cvar_t	*sv_zombietime;
extern	cvar_t	*sv_rconPassword;
extern	cvar_t	*sv_privatePassword;
extern	cvar_t	*sv_allowDownload;
extern	cvar_t	*sv_maxclients;
extern	cvar_t	*sv_maxclientsPerIP;
extern	cvar_t	*sv_clientTLD;
extern courseDetection_t currentCourse;
extern	cvar_t	*sv_privateClients;
extern	cvar_t	*sv_hostname;
extern	cvar_t	*sv_master[MAX_MASTER_SERVERS];
extern	cvar_t	*sv_reconnectlimit;
extern	cvar_t	*sv_padPackets;
extern	cvar_t	*sv_killserver;
extern	cvar_t	*sv_mapname;
extern	cvar_t	*sv_mapChecksum;
extern	cvar_t	*sv_referencedPakNames;
extern	cvar_t	*sv_serverid;
extern	cvar_t	*sv_minRate;
extern	cvar_t	*sv_maxRate;
extern	cvar_t	*sv_dlRate;
extern	cvar_t	*sv_gametype;
extern	cvar_t	*sv_pure;
extern	cvar_t	*sv_floodProtect;
extern	cvar_t	*sv_lanForceRate;

#ifdef USE_AUTH
extern	cvar_t	*sv_authServerIP;
extern	cvar_t	*sv_auth_engine;
#endif

extern	cvar_t *sv_levelTimeReset;
extern	cvar_t *sv_filter;

#ifdef USE_BANS
extern	cvar_t	*sv_banFile;
extern	serverBan_t serverBans[SERVER_MAXBANS];
extern	int serverBansCount;
#endif

extern	cvar_t	*sv_sayprefix;
extern	cvar_t	*sv_tellprefix;

extern	cvar_t *sv_gotoMsgBigtext;
extern  cvar_t  *sv_nofallDamage;
extern  cvar_t  *sv_infiniteStamina;
extern cvar_t *mod_ghostRadius;

//===========================================================

//
// sv_main.c
//
qboolean SVC_RateLimit( rateLimit_t *bucket, int burst, int period );
qboolean SVC_RateLimitAddress( const netadr_t *from, int burst, int period );
void SVC_RateRestoreBurstAddress( const netadr_t *from, int burst, int period );
void SVC_RateRestoreToxicAddress( const netadr_t *from, int burst, int period );
void SVC_RateDropAddress( const netadr_t *from, int burst, int period );

void SV_FinalMessage( const char *message );
void QDECL SV_SendServerCommand( client_t *cl, const char *fmt, ...) __attribute__ ((format (printf, 2, 3)));

void SV_AddOperatorCommands( void );
void SV_RemoveOperatorCommands( void );

void SV_MasterShutdown( void );
int SV_RateMsec( const client_t *client );


//
// sv_init.c
//
void SV_SetConfigstring( int index, const char *val );
void SV_GetConfigstring( int index, char *buffer, int bufferSize );
void SV_UpdateConfigstrings( client_t *client );

void SV_SetUserinfo( int index, const char *val );
void SV_GetUserinfo( int index, char *buffer, int bufferSize );

void SV_ChangeMaxClients( void );
void SV_SpawnServer( const char *mapname, qboolean killBots );


//
// sv_client.c
//
void SV_GetChallenge( const netadr_t *from );
void SV_InitChallenger( void );

void SV_DirectConnect( const netadr_t *from );

void SV_ExecuteClientMessage( client_t *cl, msg_t *msg );
void SV_UserinfoChanged( client_t *cl, qboolean updateUserinfo, qboolean runFilter );

void SV_ClientEnterWorld( client_t *client, usercmd_t *cmd );
void SV_FreeClient( client_t *client );
void SV_DropClient( client_t *drop, const char *reason );

qboolean SV_ExecuteClientCommand( client_t *cl, const char *s );
void SV_ClientThink( client_t *cl, usercmd_t *cmd );

int SV_SendDownloadMessages( void );
int SV_SendQueuedMessages( void );

void SV_FreeIP4DB( void );
void SV_PrintLocations_f( client_t *client );

#ifdef USE_AUTH
void SV_Auth_DropClient(client_t *drop, const char *reason, const char *message);
#endif


//
// sv_ccmds.c
//
void SV_Heartbeat_f( void );
client_t *SV_GetPlayerByHandle( void );

//
// sv_snapshot.c
//
void SV_AddServerCommand( client_t *client, const char *cmd );
void SV_UpdateServerCommandsToClient( client_t *client, msg_t *msg );
void SV_WriteFrameToClient( client_t *client, msg_t *msg );
void SV_SendMessageToClient( msg_t *msg, client_t *client );
void SV_SendClientMessages( void );
void SV_SendClientSnapshot( client_t *client );

void SV_InitSnapshotStorage( void );
void SV_IssueNewSnapshot( void );

int SV_RemainingGameState( void );

//
// sv_game.c
//
int	SV_NumForGentity( sharedEntity_t *ent );
int SV_GetClientTeam(int clientNum);
extern int playerStatsOffsets[1][OFFSET_PS_MAX];
int getVersion(void);
sharedEntity_t *SV_GentityNum( int num );
playerState_t *SV_GameClientNum( int num );
svEntity_t	*SV_SvEntityForGentity( sharedEntity_t *gEnt );
sharedEntity_t *SV_GEntityForSvEntity( svEntity_t *svEnt );
void		SV_InitGameProgs ( void );
void		SV_ShutdownGameProgs ( void );
void		SV_RestartGameProgs( void );
qboolean	SV_inPVS (const vec3_t p1, const vec3_t p2);

//
// sv_bot.c
//
void		SV_BotFrame( int time );
int			SV_BotAllocateClient(void);
void		SV_BotFreeClient( int clientNum );

void		SV_BotInitCvars(void);
int			SV_BotLibSetup( void );
int			SV_BotLibShutdown( void );
int			SV_BotGetSnapshotEntity( int client, int ent );
int			SV_BotGetConsoleMessage( int client, char *buf, int size );

int BotImport_DebugPolygonCreate(int color, int numPoints, vec3_t *points);
void BotImport_DebugPolygonDelete(int id);

void SV_BotInitBotLib(void);

//============================================================
//
// high level object sorting to reduce interaction tests
//

void SV_ClearWorld (void);
// called after the world model has been loaded, before linking any entities

void SV_UnlinkEntity( sharedEntity_t *ent );
// call before removing an entity, and before trying to move one,
// so it doesn't clip against itself

void SV_LinkEntity( sharedEntity_t *ent );
// Needs to be called any time an entity changes origin, mins, maxs,
// or solid.  Automatically unlinks if needed.
// sets ent->r.absmin and ent->r.absmax
// sets ent->leafnums[] for pvs determination even if the entity
// is not solid


clipHandle_t SV_ClipHandleForEntity( const sharedEntity_t *ent );


void SV_SectorList_f( void );


int SV_AreaEntities( const vec3_t mins, const vec3_t maxs, int *entityList, int maxcount );
// fills in a table of entity numbers with entities that have bounding boxes
// that intersect the given area.  It is possible for a non-axial bmodel
// to be returned that doesn't actually intersect the area on an exact
// test.
// returns the number of pointers filled in
// The world entity is never returned in this list.


int SV_PointContents( const vec3_t p, int passEntityNum );
// returns the CONTENTS_* value from the world and all entities at the given point.


void SV_Trace( trace_t *results, const vec3_t start, const vec3_t mins, const vec3_t maxs, const vec3_t end, int passEntityNum, int contentmask, qboolean capsule );
// mins and maxs are relative

// if the entire move stays in a solid volume, trace.allsolid will be set,
// trace.startsolid will be set, and trace.fraction will be 0

// if the starting point is in a solid, it will be allowed to move out
// to an open area

// passEntityNum is explicitly excluded from clipping checks (normally ENTITYNUM_NONE)


void SV_ClipToEntity( trace_t *trace, const vec3_t start, const vec3_t mins, const vec3_t maxs, const vec3_t end, int entityNum, int contentmask, qboolean capsule );
// clip to a specific entity

//
// sv_net_chan.c
//
void SV_Netchan_Transmit( client_t *client, msg_t *msg);
int SV_Netchan_TransmitNextFragment( client_t *client );
qboolean SV_Netchan_Process( client_t *client, msg_t *msg );
void SV_Netchan_FreeQueue( client_t *client );

//
// sv_filter.c
//
void SV_LoadFilters( const char *filename );
const char *SV_RunFilters( const char *userinfo, const netadr_t *addr );
void SV_AddFilter_f( void );
void SV_AddFilterCmd_f( void );


