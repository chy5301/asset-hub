export interface paths {
    "/api/types": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Types */
        get: operations["list_types_api_types_get"];
        put?: never;
        /** Create Type */
        post: operations["create_type_api_types_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/types/{type_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Type */
        get: operations["get_type_api_types__type_id__get"];
        put?: never;
        post?: never;
        /** Delete Type */
        delete: operations["delete_type_api_types__type_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Type
         * @description 部分更新 type。code_prefix immutable（DTO 已不暴露此字段）。
         */
        patch: operations["update_type_api_types__type_id__patch"];
        trace?: never;
    };
    "/api/assets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Assets */
        get: operations["list_assets_api_assets_get"];
        put?: never;
        /** Create Asset */
        post: operations["create_asset_api_assets_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Asset */
        get: operations["get_asset_api_assets__asset_id__get"];
        put?: never;
        post?: never;
        /**
         * Delete Asset
         * @description 删除资产 cascade（StateTransitionRecord + Attachment FS+DB）。
         */
        delete: operations["delete_asset_api_assets__asset_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Asset
         * @description 更新资产非状态字段（name/serial_number/notes/custom_data/acquired_at）。
         *
         *     状态、holder、location 走 POST /api/assets/{id}/transitions。
         */
        patch: operations["update_asset_api_assets__asset_id__patch"];
        trace?: never;
    };
    "/api/assets/{asset_id}/transitions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Transitions */
        get: operations["list_transitions_api_assets__asset_id__transitions_get"];
        put?: never;
        /** Create Transition */
        post: operations["create_transition_api_assets__asset_id__transitions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Attachments */
        get: operations["list_attachments_api_assets__asset_id__attachments_get"];
        put?: never;
        /** Upload Attachment */
        post: operations["upload_attachment_api_assets__asset_id__attachments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/attachments/{attachment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Attachment */
        get: operations["get_attachment_api_attachments__attachment_id__get"];
        put?: never;
        post?: never;
        /** Delete Attachment */
        delete: operations["delete_attachment_api_attachments__attachment_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/attachments/{attachment_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download Attachment */
        get: operations["download_attachment_api_attachments__attachment_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Assets
         * @description spec §2.1: 单端点 CSV/XLSX 导出. format 必填; filter 复用 list.
         */
        get: operations["export_assets_api_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Stats */
        get: operations["get_stats_api_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/healthz": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Healthz */
        get: operations["healthz_api_healthz_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AssetCreate */
        AssetCreate: {
            /** Name */
            name: string;
            /**
             * Type Id
             * Format: uuid
             */
            type_id: string;
            /** Serial Number */
            serial_number?: string | null;
            /** Brand */
            brand?: string | null;
            /** Model */
            model?: string | null;
            /** Holder */
            holder?: string | null;
            /** Location */
            location?: string | null;
            /** Notes */
            notes?: string | null;
            /** Custom Data */
            custom_data?: {
                [key: string]: unknown;
            };
            /** Acquired At */
            acquired_at?: string | null;
        };
        /** AssetRead */
        AssetRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Asset Code */
            asset_code: string;
            /** Name */
            name: string;
            /** Serial Number */
            serial_number: string | null;
            /** Brand */
            brand: string | null;
            /** Model */
            model: string | null;
            /**
             * Type Id
             * Format: uuid
             */
            type_id: string;
            /** Type Name */
            type_name: string | null;
            status: components["schemas"]["AssetStatus"];
            /** Holder */
            holder: string | null;
            /** Location */
            location: string | null;
            /** Notes */
            notes: string | null;
            /** Custom Data */
            custom_data: {
                [key: string]: unknown;
            };
            /** Acquired At */
            acquired_at: string | null;
            /** Idle Days */
            idle_days?: number | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * AssetStatus
         * @enum {string}
         */
        AssetStatus: "IDLE" | "IN_USE" | "MAINTENANCE" | "BROKEN" | "RETIRED" | "DISPOSED";
        /**
         * AssetUpdate
         * @description 注意：
         *     - type_id 不暴露——D9 编辑表单禁改 type；
         *     - asset_code 不暴露——系统生成、不允许手改；
         *     - status/holder/location 不暴露——M3a 后必须走 POST /api/assets/{id}/transitions，经 state machine 校验。
         */
        AssetUpdate: {
            /** Name */
            name?: string | null;
            /** Serial Number */
            serial_number?: string | null;
            /** Brand */
            brand?: string | null;
            /** Model */
            model?: string | null;
            /** Notes */
            notes?: string | null;
            /** Custom Data */
            custom_data?: {
                [key: string]: unknown;
            } | null;
            /** Acquired At */
            acquired_at?: string | null;
        };
        /**
         * AttachmentKind
         * @enum {string}
         */
        AttachmentKind: "photo" | "invoice" | "doc" | "other";
        /** AttachmentRead */
        AttachmentRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            kind: components["schemas"]["AttachmentKind"];
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Mime Type */
            mime_type: string;
            /** Original Name */
            original_name: string;
            /**
             * Uploaded At
             * Format: date-time
             */
            uploaded_at: string;
        };
        /** Body_upload_attachment_api_assets__asset_id__attachments_post */
        Body_upload_attachment_api_assets__asset_id__attachments_post: {
            /** File */
            file: string;
            /** @default other */
            kind: components["schemas"]["AttachmentKind"];
        };
        /**
         * CustomFieldDef
         * @description v1 schema：key + label + type + required + options + 扩展属性。
         *
         *     M2c-3 D2 决议：字段名沿用 M1/M2 的 `key`（与 services/validation.py:8 + 现有 fixtures 一致），
         *     不重命名为 name；spec D2 文案随 plan Task 15 同步使用 `key`（前端 FieldDef 也用 key）。
         */
        CustomFieldDef: {
            /** Key */
            key: string;
            /** Label */
            label?: string | null;
            /** Type */
            type: string;
            /**
             * Required
             * @default false
             */
            required: boolean;
            /** Default */
            default?: string | number | boolean | null;
            /** Placeholder */
            placeholder?: string | null;
            /** Help */
            help?: string | null;
            /** Unit */
            unit?: string | null;
            /** Min */
            min?: number | null;
            /** Max */
            max?: number | null;
            /** Options */
            options?: string[] | null;
            /** Displayas */
            displayAs?: string | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HolderRankingItem */
        HolderRankingItem: {
            /** Holder */
            holder: string;
            /** Count */
            count: number;
        };
        /** IdleTopItem */
        IdleTopItem: {
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            /** Asset Code */
            asset_code: string;
            /** Name */
            name: string;
            /** Type Name */
            type_name: string | null;
            /** Current Location */
            current_location: string | null;
            /** Idle Days */
            idle_days: number;
            /**
             * Idle Since
             * Format: date-time
             */
            idle_since: string;
        };
        /**
         * StatsRead
         * @description 4 段聚合响应 + summary。各段在响应里通过 fields 子集控制；summary 始终返回.
         */
        StatsRead: {
            /** Type Distribution */
            type_distribution?: components["schemas"]["TypeDistributionItem"][] | null;
            /** Status Distribution */
            status_distribution?: {
                [key: string]: number;
            } | null;
            /** Holder Ranking */
            holder_ranking?: components["schemas"]["HolderRankingItem"][] | null;
            /** Idle Top */
            idle_top?: components["schemas"]["IdleTopItem"][] | null;
            summary: components["schemas"]["StatsSummary"];
        };
        /**
         * StatsSummary
         * @description 业务摘要——命名 summary 而非 metadata，避免与 CLI envelope 顶层 metadata 冲突.
         */
        StatsSummary: {
            /** Total Assets */
            total_assets: number;
            /** Registered Assets */
            registered_assets: number;
            /** Idle Count */
            idle_count: number;
            /** Include Retired */
            include_retired: boolean;
            /** Include Disposed */
            include_disposed: boolean;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
        };
        /** TransitionCreate */
        TransitionCreate: {
            kind: components["schemas"]["TransitionKind"];
            /** To Holder */
            to_holder?: string | null;
            /** To Location */
            to_location?: string | null;
            /** Note */
            note?: string | null;
            /** Due At */
            due_at?: string | null;
        };
        /**
         * TransitionKind
         * @enum {string}
         */
        TransitionKind: "CHECKOUT_INTERNAL" | "CHECKOUT_EXTERNAL" | "RETURN" | "SEND_TO_MAINTENANCE" | "RECOVER_FROM_MAINTENANCE" | "RETIRE" | "REINSTATE" | "DISPOSE" | "REASSIGN" | "REPORT_BROKEN" | "DECLARE_UNREPAIRABLE" | "DISMISS";
        /** TransitionRead */
        TransitionRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            kind: components["schemas"]["TransitionKind"];
            from_status: components["schemas"]["AssetStatus"];
            to_status: components["schemas"]["AssetStatus"];
            /** From Holder */
            from_holder: string | null;
            /** To Holder */
            to_holder: string | null;
            /** From Location */
            from_location: string | null;
            /** To Location */
            to_location: string | null;
            /** Note */
            note: string | null;
            /** Due At */
            due_at: string | null;
            /** Closes Transition Id */
            closes_transition_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** TypeCreate */
        TypeCreate: {
            /** Name */
            name: string;
            /** Code Prefix */
            code_prefix: string;
            /** Description */
            description?: string | null;
            /**
             * Custom Fields
             * @default []
             */
            custom_fields: components["schemas"]["CustomFieldDef"][];
        };
        /** TypeDistributionItem */
        TypeDistributionItem: {
            /**
             * Type Id
             * Format: uuid
             */
            type_id: string;
            /** Type Name */
            type_name: string;
            /** Count */
            count: number;
        };
        /** TypeRead */
        TypeRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Code Prefix */
            code_prefix: string;
            /** Description */
            description: string | null;
            /** Custom Fields */
            custom_fields: components["schemas"]["CustomFieldDef"][];
            /**
             * Ref Count
             * @default 0
             */
            ref_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * TypeUpdate
         * @description 注意：code_prefix immutable，update DTO 不暴露此字段（D5）。
         */
        TypeUpdate: {
            /** Name */
            name?: string | null;
            /** Description */
            description?: string | null;
            /** Custom Fields */
            custom_fields?: components["schemas"]["CustomFieldDef"][] | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_types_api_types_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"][];
                };
            };
        };
    };
    create_type_api_types_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TypeCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_type_api_types__type_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                type_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_type_api_types__type_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                type_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_type_api_types__type_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                type_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TypeUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_assets_api_assets_get: {
        parameters: {
            query?: {
                type_id?: string | null;
                status?: components["schemas"]["AssetStatus"] | null;
                holder?: string | null;
                q?: string | null;
                include_retired?: boolean;
                include_disposed?: boolean;
                sort_by?: ("name" | "brand" | "model" | "asset_code" | "serial_number" | "created_at" | "updated_at" | "acquired_at" | "idle_days") | null;
                sort_order?: "asc" | "desc";
                limit?: number | null;
                offset?: number | null;
                fields?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_asset_api_assets_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_asset_api_assets__asset_id__get: {
        parameters: {
            query?: {
                fields?: string | null;
            };
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_asset_api_assets__asset_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_asset_api_assets__asset_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_transitions_api_assets__asset_id__transitions_get: {
        parameters: {
            query?: {
                fields?: string | null;
            };
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TransitionRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_transition_api_assets__asset_id__transitions_post: {
        parameters: {
            query?: {
                fields?: string | null;
            };
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TransitionCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TransitionRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_attachments_api_assets__asset_id__attachments_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_attachment_api_assets__asset_id__attachments_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_attachment_api_assets__asset_id__attachments_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_attachment_api_attachments__attachment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_attachment_api_attachments__attachment_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_attachment_api_attachments__attachment_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_assets_api_export_get: {
        parameters: {
            query: {
                format: "csv" | "xlsx";
                type_id?: string | null;
                status?: components["schemas"]["AssetStatus"] | null;
                holder?: string | null;
                q?: string | null;
                include_retired?: boolean;
                include_disposed?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_stats_api_stats_get: {
        parameters: {
            query?: {
                include_retired?: boolean;
                include_disposed?: boolean;
                fields?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StatsRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    healthz_api_healthz_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
