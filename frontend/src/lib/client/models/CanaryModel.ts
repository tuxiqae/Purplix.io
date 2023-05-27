/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { DomainVerification } from './DomainVerification';
import type { PublicKeyModel } from './PublicKeyModel';

export type CanaryModel = {
    domain: string;
    about: string;
    signature: string;
    algorithms?: string;
    _id: any;
    logo?: (null | string);
    user_id: any;
    created: string;
    keypair: PublicKeyModel;
    domain_verification: DomainVerification;
};

