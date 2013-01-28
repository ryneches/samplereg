drop table if exists users;
create table users (
    id integer primary key autoincrement,
    username    string not null unique,
    password    string not null,
    realname    string not null,
    city        string not null,
    state       string not null,
    country     string not null,
    team        string not null,
    avatar      string not null
);

drop table if exists records;
create table records (
    id integer primary key autoincrement,
    identifier          string not null,
    user                string not null,
    date                integer,
    lat                 real,
    lng                 real,
    surface_material    string not null,
    surface_condition   string not null,
    surface_humidity    string not null,
    context_type        string not null,
    inorout             string not null,
    direct_sunlight     boolean,
    temp                real,
    closeup             string not null,
    context             string not null,
    name                string not null,
    description         string not null,
    audited             boolean
);


